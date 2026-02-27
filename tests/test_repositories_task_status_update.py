import sys
import types
import unittest

gspread_module = types.ModuleType("gspread")
gspread_utils = types.ModuleType("gspread.utils")
gspread_utils.rowcol_to_a1 = lambda *_args, **_kwargs: "A1"
gspread_module.utils = gspread_utils
sys.modules.setdefault("gspread", gspread_module)
sys.modules.setdefault("gspread.utils", gspread_utils)

google_module = types.ModuleType("google")
oauth2_module = types.ModuleType("google.oauth2")
service_account_module = types.ModuleType("google.oauth2.service_account")
service_account_module.Credentials = types.SimpleNamespace(
    from_service_account_file=lambda *_args, **_kwargs: None
)
oauth2_module.service_account = service_account_module
google_module.oauth2 = oauth2_module
sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.oauth2", oauth2_module)
sys.modules.setdefault("google.oauth2.service_account", service_account_module)

dotenv_module = types.ModuleType("dotenv")
dotenv_module.load_dotenv = lambda *_args, **_kwargs: None
dotenv_module.dotenv_values = lambda *_args, **_kwargs: {}
sys.modules.setdefault("dotenv", dotenv_module)

pytz_module = types.ModuleType("pytz")
pytz_module.timezone = lambda *_args, **_kwargs: None
sys.modules.setdefault("pytz", pytz_module)

from data.repositories import Repositories
from domain import models


class _FakeClient:
    def __init__(self, header, data):
        self._header = header
        self._data = data
        self.updated_rows = []

    def read_rows_with_header(self, _sheet_name):
        return self._header, self._data

    def update_row(self, _sheet_name, row_idx, row):
        self.updated_rows.append((row_idx, row))


class TaskStatusUpdateTests(unittest.TestCase):
    def test_terminal_status_updates_all_matching_rows(self):
        header = ["怪物ID", "玩家", "怪物名稱", "開始日", "截止日", "狀態"]
        data = [
            ["M1", "P1", "Slime", "2026-02-27", "2026-02-28", "進行中"],
            ["M1", "P1", "Slime", "2026-02-27", "2026-02-28", "進行中"],
        ]
        client = _FakeClient(header, data)
        repo = Repositories(client)
        task = models.Task(
            monster_id="M1",
            player="P1",
            name="Slime",
            difficulty="E",
            content="Run",
            start_date="2026-02-27",
            deadline="2026-02-28",
            status="擊殺",
        )

        ok = repo.update_task_status(task)

        self.assertTrue(ok)
        self.assertEqual(len(client.updated_rows), 2)

    def test_relaxed_match_updates_when_id_column_missing(self):
        header = ["玩家", "怪物名稱", "狀態"]
        data = [
            ["P1", "Slime", "進行中"],
            ["P1", "Slime", "進行中"],
        ]
        client = _FakeClient(header, data)
        repo = Repositories(client)
        task = models.Task(
            monster_id="M1",
            player="P1",
            name="Slime",
            difficulty="E",
            content="Run",
            start_date="2026-02-27",
            deadline="2026-02-28",
            status="擊殺",
        )

        ok = repo.update_task_status(task)

        self.assertTrue(ok)
        self.assertGreaterEqual(len(client.updated_rows), 1)
        self.assertTrue(any("擊殺" in str(row[2]) for _, row in client.updated_rows))


if __name__ == "__main__":
    unittest.main()
