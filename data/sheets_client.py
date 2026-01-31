"""
gspread wrapper: centralizes all direct Sheet I/O and basic concurrency checks.

Responsibilities:
- Initialize client from service account JSON.
- Read worksheets as lists/dicts.
- Single-row update/append with optional version/timestamp checks.
- Provide lightweight retry for common contention.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from config import settings


class SheetsClient:
    def __init__(self) -> None:
        settings.require_settings()
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(settings.SERVICE_ACCOUNT_JSON, scopes=scopes)
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(settings.SHEET_ID)
        self._ws_cache: Dict[str, gspread.Worksheet] = {}
        self._read_cache: Dict[str, Tuple[float, List[List[str]]]] = {}
        self._read_ttl_sec = 30.0

    def worksheet(self, name: str):
        cached = self._ws_cache.get(name)
        if cached is not None:
            return cached
        ws = self.sh.worksheet(name)
        self._ws_cache[name] = ws
        return ws

    def _invalidate_cache(self, sheet_name: str) -> None:
        self._read_cache.pop(sheet_name, None)

    def invalidate_cache(self, sheet_name: str) -> None:
        self._invalidate_cache(sheet_name)

    def read_rows(self, sheet_name: str) -> List[List[str]]:
        cached = self._read_cache.get(sheet_name)
        if cached:
            ts, rows = cached
            if time.time() - ts < self._read_ttl_sec:
                return rows
        ws = self.worksheet(sheet_name)
        rows = ws.get_all_values()
        self._read_cache[sheet_name] = (time.time(), rows)
        return rows

    def read_rows_with_header(self, sheet_name: str) -> Tuple[List[str], List[List[str]]]:
        rows = self.read_rows(sheet_name)
        if not rows:
            return [], []
        header, *data = rows
        return header, data

    def append_row(self, sheet_name: str, row: List[Any]) -> None:
        ws = self.worksheet(sheet_name)
        ws.append_row(row, value_input_option="USER_ENTERED")
        self._invalidate_cache(sheet_name)

    def update_row(self, sheet_name: str, row_idx: int, row: List[Any]) -> None:
        ws = self.worksheet(sheet_name)
        end_col = max(1, len(row))
        start = rowcol_to_a1(row_idx, 1)
        end = rowcol_to_a1(row_idx, end_col)
        ws.update(f"{start}:{end}", [row])
        self._invalidate_cache(sheet_name)

    def update_ranges(self, sheet_name: str, updates: List[Tuple[str, List[List[Any]]]]) -> None:
        if not updates:
            return
        ws = self.worksheet(sheet_name)
        payload = [{"range": rng, "values": values} for rng, values in updates]
        ws.batch_update(payload)
        self._invalidate_cache(sheet_name)

    def delete_row(self, sheet_name: str, row_idx: int) -> None:
        ws = self.worksheet(sheet_name)
        ws.delete_rows(row_idx)
        self._invalidate_cache(sheet_name)

    def delete_rows(self, sheet_name: str, start_row: int, end_row: Optional[int] = None) -> None:
        ws = self.worksheet(sheet_name)
        if end_row is not None:
            if end_row < start_row:
                return
            ws.delete_rows(start_row, end_row)
        else:
            ws.delete_rows(start_row)
        self._invalidate_cache(sheet_name)

    def safe_update(
        self,
        sheet_name: str,
        row_idx: int,
        row: List[Any],
        version_col: Optional[int] = None,
        expected_version: Optional[str] = None,
        retry: int = 1,
    ) -> bool:
        """
        Optionally compare a version cell before writing; on mismatch return False.
        """
        ws = self.worksheet(sheet_name)
        for _ in range(retry + 1):
            if version_col and expected_version is not None:
                current = ws.cell(row_idx, version_col).value
                if current != expected_version:
                    return False
            end_col = max(1, len(row))
            start = rowcol_to_a1(row_idx, 1)
            end = rowcol_to_a1(row_idx, end_col)
            ws.update(f"{start}:{end}", [row])
            if version_col:
                ws.update_cell(row_idx, version_col, str(time.time()))
            self._invalidate_cache(sheet_name)
            return True
        return False
