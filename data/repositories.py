"""
Repository layer mapping worksheets to typed records.

Each function should only contain mapping/parsing logic and delegate IO to SheetsClient.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from data.sheets_client import SheetsClient
from domain import models
from gspread.utils import rowcol_to_a1


def _col_index(header: List[str], name: str, default: int = 0) -> int:
    return header.index(name) if name in header else default


def _col_index_any(header: List[str], names: List[str], default: int = 0) -> int:
    for name in names:
        if name in header:
            return header.index(name)
    for idx, head in enumerate(header):
        for name in names:
            if name and name in head:
                return idx
    return default


def _set_value(header: List[str], row: List[str], names: List[str], value) -> None:
    idx = _col_index_any(header, names, default=-1)
    if idx >= 0 and idx < len(row):
        row[idx] = value


def _find_row_by_value(data: List[List[str]], col_idx: int, value: str) -> Optional[int]:
    target = str(value).strip() if value is not None else ""
    for idx, row in enumerate(data, start=2):  # +2 because sheet rows are 1-based and row 1 is header
        if len(row) <= col_idx:
            continue
        cell = str(row[col_idx]).strip()
        if cell == target:
            return idx
    return None


class Repositories:
    def __init__(self, client: SheetsClient) -> None:
        self.client = client

    def get_player_states(self) -> List[models.PlayerState]:
        rows = self.client.read_rows("角色狀態表")
        return models.PlayerState.from_rows(rows)

    def get_job_options(self) -> List[tuple[str, str]]:
        rows = self.client.read_rows("清單表")
        if not rows:
            return []
        results = []
        for row in rows[2:7]:
            if len(row) <= 2:
                continue
            code = str(row[1]).strip()
            name = str(row[2]).strip()
            if code or name:
                results.append((code, name))
        return results

    def get_job_base_stats(self, job_code: str) -> tuple[int, int]:
        rows = self.client.read_rows("等級資料表")
        if not rows:
            return 0, 0
        for row in rows[1:]:
            if len(row) <= 7:
                continue
            code = str(row[5]).strip()
            if code != job_code:
                continue
            try:
                base_hp = int(float(str(row[6]).strip() or 0))
            except Exception:
                base_hp = 0
            try:
                base_mp = int(float(str(row[7]).strip() or 0))
            except Exception:
                base_mp = 0
            return base_hp, base_mp
        return 0, 0

    def get_job_skill_pool(self, job_code: str) -> List[models.SkillState]:
        header, data = self.client.read_rows_with_header("職業技能表")
        if not header:
            return []
        col_job = _col_index_any(header, ["職業代碼", "職業", "職業ID"])
        col_skill = _col_index_any(header, ["技能ID", "技能編碼", "技能代碼"])
        col_name = _col_index_any(header, ["技能名稱", "名稱"])
        col_kind = _col_index_any(header, ["主被動"])
        col_mp = _col_index_any(header, ["MP消耗", "消耗MP"])
        col_total = _col_index_any(header, ["每週可用總次數", "每週可用次數"])
        col_reset = _col_index_any(header, ["重置規則"])
        col_desc = _col_index_any(header, ["技能效果說明", "技能敘述", "技能描述", "敘述"])
        col_enabled = _col_index_any(header, ["啟用狀態"])
        results: List[models.SkillState] = []
        for row in data:
            if len(row) <= max(col_job, col_skill):
                continue
            if str(row[col_job]).strip() != job_code:
                continue
            skill_id = str(row[col_skill]).strip()
            if not skill_id:
                continue
            name = str(row[col_name]).strip() if col_name < len(row) else ""
            kind = str(row[col_kind]).strip() if col_kind < len(row) else ""
            try:
                mp_cost = int(float(str(row[col_mp]).strip() or 0))
            except Exception:
                mp_cost = 0
            try:
                total_uses = int(float(str(row[col_total]).strip()))
            except Exception:
                total_uses = None
            reset_rule = str(row[col_reset]).strip() if col_reset < len(row) else ""
            desc = str(row[col_desc]).strip() if col_desc < len(row) else ""
            if desc.startswith("#ERROR"):
                desc = ""
            enabled = str(row[col_enabled]).strip() if col_enabled < len(row) else "Y"
            results.append(
                models.SkillState(
                    player="",
                    job=job_code,
                    skill_id=skill_id,
                    name=name,
                    kind=kind,
                    mp_cost=mp_cost,
                    enabled=enabled,
                    total_uses=total_uses,
                    remaining=total_uses,
                    reset_rule=reset_rule,
                    description=desc,
                )
            )
        return results

    def get_skill_definition(self, skill_id: str) -> Optional[models.SkillState]:
        header, data = self.client.read_rows_with_header("職業技能表")
        if not header:
            return None
        col_skill = _col_index_any(header, ["技能ID", "技能編碼", "技能代碼"])
        col_name = _col_index_any(header, ["技能名稱", "名稱"])
        col_kind = _col_index_any(header, ["主被動"])
        col_mp = _col_index_any(header, ["MP消耗", "消耗MP"])
        col_total = _col_index_any(header, ["每週可用總次數", "每週可用次數"])
        col_reset = _col_index_any(header, ["重置規則"])
        col_desc = _col_index_any(header, ["技能效果說明", "技能敘述", "技能描述", "敘述"])
        col_enabled = _col_index_any(header, ["啟用狀態"])
        for row in data:
            if len(row) <= col_skill:
                continue
            if str(row[col_skill]).strip() != skill_id:
                continue
            name = str(row[col_name]).strip() if col_name < len(row) else ""
            kind = str(row[col_kind]).strip() if col_kind < len(row) else ""
            try:
                mp_cost = int(float(str(row[col_mp]).strip() or 0))
            except Exception:
                mp_cost = 0
            try:
                total_uses = int(float(str(row[col_total]).strip()))
            except Exception:
                total_uses = None
            reset_rule = str(row[col_reset]).strip() if col_reset < len(row) else ""
            desc = str(row[col_desc]).strip() if col_desc < len(row) else ""
            if desc.startswith("#ERROR"):
                desc = ""
            enabled = str(row[col_enabled]).strip() if col_enabled < len(row) else "Y"
            return models.SkillState(
                player="",
                job="",
                skill_id=skill_id,
                name=name,
                kind=kind,
                mp_cost=mp_cost,
                enabled=enabled,
                total_uses=total_uses,
                remaining=total_uses,
                reset_rule=reset_rule,
                description=desc,
            )
        return None

    def replace_skill_states(self, states: List[models.SkillState]) -> int:
        header, data = self.client.read_rows_with_header("技能狀態")
        if not header:
            return 0
        if data:
            self.client.delete_rows("技能狀態", 2, len(data) + 1)
        for state in states:
            row = ["" for _ in range(len(header))]
            _set_value(header, row, ["玩家"], state.player)
            _set_value(header, row, ["職業"], state.job)
            _set_value(header, row, ["技能ID", "技能編碼"], state.skill_id)
            _set_value(header, row, ["技能名稱"], state.name)
            _set_value(header, row, ["主被動"], state.kind)
            _set_value(header, row, ["MP消耗", "消耗MP"], state.mp_cost)
            _set_value(header, row, ["啟用狀態"], state.enabled)
            _set_value(
                header,
                row,
                ["每週可用總次數", "每週可用次數"],
                state.total_uses if state.total_uses is not None else "",
            )
            _set_value(header, row, ["剩餘次數"], state.remaining if state.remaining is not None else "")
            _set_value(header, row, ["重置規則"], state.reset_rule)
            _set_value(header, row, ["技能效果說明", "技能敘述"], state.description)
            self.client.append_row("技能狀態", row)
        return len(states)

    def replace_player_states(self, states: List[models.PlayerState]) -> int:
        header, data = self.client.read_rows_with_header("角色狀態表")
        if not header:
            return 0
        if data:
            self.client.delete_rows("角色狀態表", 2, len(data) + 1)
        for state in states:
            row = ["" for _ in range(len(header))]
            _set_value(header, row, ["玩家"], state.name)
            _set_value(header, row, ["職業"], state.job)
            _set_value(header, row, ["等級"], state.level)
            _set_value(header, row, ["EXP"], state.exp)
            _set_value(header, row, ["HP當前"], state.hp_current)
            _set_value(header, row, ["MP當前"], state.mp_current)
            _set_value(header, row, ["HP上限"], state.hp_max)
            _set_value(header, row, ["MP上限"], state.mp_max)
            _set_value(header, row, ["技能摘要"], state.skill_summary)
            _set_value(
                header,
                row,
                ["MP歸零剩餘週數", "MP歸零剩餘", "懲罰剩餘週數", "懲罰週數"],
                state.penalty_weeks,
            )
            _set_value(header, row, ["HP"], f"{state.hp_current}/{state.hp_max}")
            _set_value(header, row, ["MP"], f"{state.mp_current}/{state.mp_max}")
            self.client.append_row("角色狀態表", row)
        return len(states)

    def save_player_state(self, state: models.PlayerState) -> bool:
        header, data = self.client.read_rows_with_header("角色狀態表")
        name_col = _col_index(header, "玩家")
        row_idx = _find_row_by_value(data, name_col, state.name)
        if not row_idx:
            return False
        existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
        row = existing + ["" for _ in range(len(header) - len(existing))]
        _set_value(header, row, ["玩家"], state.name)
        _set_value(header, row, ["職業"], state.job)
        _set_value(header, row, ["等級"], state.level)
        _set_value(header, row, ["EXP"], state.exp)
        _set_value(header, row, ["HP當前"], state.hp_current)
        _set_value(header, row, ["MP當前"], state.mp_current)
        _set_value(header, row, ["HP上限"], state.hp_max)
        _set_value(header, row, ["MP上限"], state.mp_max)
        _set_value(header, row, ["技能摘要"], state.skill_summary)
        _set_value(
            header,
            row,
            ["MP歸零剩餘週數", "MP歸零剩餘", "懲罰剩餘週數", "懲罰週數"],
            state.penalty_weeks,
        )
        _set_value(header, row, ["HP"], f"{state.hp_current}/{state.hp_max}")
        _set_value(header, row, ["MP"], f"{state.mp_current}/{state.mp_max}")
        self.client.update_row("角色狀態表", row_idx, row)
        return True

    def update_player_states_bulk(self, states: List[models.PlayerState]) -> int:
        header, data = self.client.read_rows_with_header("角色狀態表")
        if not header:
            return 0
        name_col = _col_index_any(header, ["玩家"])
        index = {}
        for idx, row in enumerate(data, start=2):
            if len(row) <= name_col:
                continue
            name = str(row[name_col]).strip()
            if name:
                index[name] = idx
        updates = []
        updated = 0
        for state in states:
            row_idx = index.get(state.name)
            if not row_idx:
                continue
            existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
            row = existing + ["" for _ in range(len(header) - len(existing))]
            _set_value(header, row, ["玩家"], state.name)
            _set_value(header, row, ["職業"], state.job)
            _set_value(header, row, ["等級"], state.level)
            _set_value(header, row, ["EXP"], state.exp)
            _set_value(header, row, ["HP當前"], state.hp_current)
            _set_value(header, row, ["MP當前"], state.mp_current)
            _set_value(header, row, ["HP上限"], state.hp_max)
            _set_value(header, row, ["MP上限"], state.mp_max)
            _set_value(header, row, ["技能摘要"], state.skill_summary)
            _set_value(
                header,
                row,
                ["MP歸零剩餘週數", "MP歸零剩餘", "懲罰剩餘週數", "懲罰週數"],
                state.penalty_weeks,
            )
            _set_value(header, row, ["HP"], f"{state.hp_current}/{state.hp_max}")
            _set_value(header, row, ["MP"], f"{state.mp_current}/{state.mp_max}")
            start = rowcol_to_a1(row_idx, 1)
            end = rowcol_to_a1(row_idx, len(row))
            updates.append((f"{start}:{end}", [row]))
            updated += 1
        if updates:
            self.client.update_ranges("角色狀態表", updates)
        return updated

    def get_tasks(self) -> List[models.Task]:
        rows = self.client.read_rows("任務列表")
        return models.Task.from_rows(rows)

    def add_task(self, task: models.Task) -> None:
        header, _ = self.client.read_rows_with_header("任務列表")
        row = ["" for _ in range(len(header))]
        _set_value(header, row, ["怪物ID", "怪物編號", "怪物編碼"], task.monster_id)
        _set_value(header, row, ["玩家"], task.player)
        _set_value(header, row, ["怪物名稱"], task.name)
        _set_value(header, row, ["難度"], task.difficulty)
        _set_value(header, row, ["任務內容"], task.content)
        _set_value(header, row, ["時限(天)"], task.time_limit_days or "")
        _set_value(header, row, ["成功EXP"], task.success_exp)
        _set_value(header, row, ["失敗-HP", "失敗HP"], task.fail_hp)
        _set_value(header, row, ["開始日"], task.start_date or "")
        _set_value(header, row, ["截止日"], task.deadline or "")
        _set_value(header, row, ["狀態", "狀態(?/??/??)"], task.status)
        self.client.append_row("任務列表", row)

    def get_events(self) -> List[models.Event]:
        rows = self.client.read_rows("事件表")
        return models.Event.from_rows(rows)

    def get_monsters(self) -> List[models.Monster]:
        rows = self.client.read_rows("怪物表")
        return models.Monster.from_rows(rows)

    def get_skill_states(self) -> List[models.SkillState]:
        rows = self.client.read_rows("技能狀態")
        return models.SkillState.from_rows(rows)

    def get_maps(self) -> List[models.MapInfo]:
        rows = self.client.read_rows("地圖表")
        return models.MapInfo.from_rows(rows)

    def get_bosses(self) -> List[models.BossInfo]:
        rows = self.client.read_rows("BOSS")
        return models.BossInfo.from_rows(rows)

    def get_skill_states_with_header(self) -> Tuple[List[str], List[List[str]], List[models.SkillState]]:
        header, data = self.client.read_rows_with_header("技能狀態")
        rows = [header] + data if header else []
        return header, data, models.SkillState.from_rows(rows)

    def update_skill_state(self, state: models.SkillState) -> bool:
        header, data = self.client.read_rows_with_header("技能狀態")
        player_col = _col_index_any(header, ["玩家"])
        skill_col = _col_index_any(header, ["技能ID", "技能編碼"])
        row_idx = None
        for idx, row in enumerate(data, start=2):
            if len(row) <= max(player_col, skill_col):
                continue
            if row[player_col] == state.player and row[skill_col] == state.skill_id:
                row_idx = idx
                break
        if not row_idx:
            return False
        existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
        row = existing + ["" for _ in range(len(header) - len(existing))]
        _set_value(header, row, ["玩家"], state.player)
        _set_value(header, row, ["職業"], state.job)
        _set_value(header, row, ["技能ID", "技能編碼"], state.skill_id)
        _set_value(header, row, ["技能名稱"], state.name)
        _set_value(header, row, ["主被動"], state.kind)
        _set_value(header, row, ["MP消耗", "消耗MP"], state.mp_cost)
        _set_value(header, row, ["啟用狀態"], state.enabled)
        _set_value(
            header,
            row,
            ["每週可用總次數", "每週可用次數"],
            state.total_uses if state.total_uses is not None else "",
        )
        _set_value(header, row, ["剩餘次數"], state.remaining if state.remaining is not None else "")
        _set_value(header, row, ["重置規則"], state.reset_rule)
        _set_value(header, row, ["技能效果說明", "技能敘述"], state.description)
        self.client.update_row("技能狀態", row_idx, row)
        return True

    def update_skill_states_bulk(self, states: List[models.SkillState]) -> int:
        header, data = self.client.read_rows_with_header("技能狀態")
        if not header:
            return 0
        player_col = _col_index_any(header, ["玩家"])
        skill_col = _col_index_any(header, ["技能ID", "技能編碼"])
        index = {}
        for idx, row in enumerate(data, start=2):
            if len(row) <= max(player_col, skill_col):
                continue
            index[(row[player_col], row[skill_col])] = idx
        updated = 0
        for state in states:
            row_idx = index.get((state.player, state.skill_id))
            if not row_idx:
                continue
            existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
            row = existing + ["" for _ in range(len(header) - len(existing))]
            _set_value(header, row, ["玩家"], state.player)
            _set_value(header, row, ["職業"], state.job)
            _set_value(header, row, ["技能ID", "技能編碼"], state.skill_id)
            _set_value(header, row, ["技能名稱"], state.name)
            _set_value(header, row, ["主被動"], state.kind)
            _set_value(header, row, ["MP消耗", "消耗MP"], state.mp_cost)
            _set_value(header, row, ["啟用狀態"], state.enabled)
            _set_value(
                header,
                row,
                ["每週可用總次數", "每週可用次數"],
                state.total_uses if state.total_uses is not None else "",
            )
            _set_value(header, row, ["剩餘次數"], state.remaining if state.remaining is not None else "")
            _set_value(header, row, ["重置規則"], state.reset_rule)
            _set_value(header, row, ["技能效果說明", "技能敘述"], state.description)
            self.client.update_row("技能狀態", row_idx, row)
            updated += 1
        return updated

    def get_level_table(self) -> Tuple[List[int], List[int], List[int], List[int]]:
        """
        Return (levels, hp_increase, mp_increase, exp_required) from 等級資料表.
        """
        rows = self.client.read_rows("等級資料表")
        levels, hp_inc, mp_inc, exp_req = [], [], [], []
        for row in rows[1:]:
            if len(row) < 4:
                continue
            try:
                level = int(float(str(row[0]).strip()))
            except Exception:
                continue
            try:
                hp = int(float(str(row[1]).strip() or 0))
            except Exception:
                hp = 0
            try:
                mp = int(float(str(row[2]).strip() or 0))
            except Exception:
                mp = 0
            try:
                exp = int(float(str(row[3]).strip() or 0))
            except Exception:
                exp = 0
            levels.append(level)
            hp_inc.append(hp)
            mp_inc.append(mp)
            exp_req.append(exp)
        return levels, hp_inc, mp_inc, exp_req

    def update_task_status(self, task: models.Task) -> bool:
        header, data = self.client.read_rows_with_header("任務列表")
        id_col = _col_index_any(header, ["怪物ID", "怪物編號", "怪物編碼"])
        row_idx = _find_row_by_value(data, id_col, task.monster_id)
        if not row_idx:
            return False
        existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
        row = existing + ["" for _ in range(len(header) - len(existing))]
        _set_value(header, row, ["怪物ID", "怪物編號", "怪物編碼"], task.monster_id)
        _set_value(header, row, ["玩家"], task.player)
        _set_value(header, row, ["怪物名稱"], task.name)
        _set_value(header, row, ["難度"], task.difficulty)
        _set_value(header, row, ["任務內容"], task.content)
        _set_value(header, row, ["時限(天)"], task.time_limit_days or "")
        _set_value(header, row, ["成功EXP"], task.success_exp)
        _set_value(header, row, ["失敗-HP"], task.fail_hp)
        _set_value(header, row, ["開始日"], task.start_date or "")
        _set_value(header, row, ["截止日"], task.deadline or "")
        _set_value(header, row, ["狀態", "狀態(?/??/??)"], task.status)
        self.client.update_row("任務列表", row_idx, row)
        return True

    def delete_task(self, monster_id: str) -> bool:
        header, data = self.client.read_rows_with_header("任務列表")
        id_col = _col_index_any(header, ["怪物ID", "怪物編號", "怪物編碼"])
        row_idx = _find_row_by_value(data, id_col, monster_id)
        if not row_idx:
            return False
        self.client.delete_row("任務列表", row_idx)
        return True

    def clear_sheet_data(self, sheet_name: str) -> int:
        rows = self.client.read_rows(sheet_name)
        if len(rows) <= 1:
            return 0
        self.client.delete_rows(sheet_name, 2, len(rows))
        return len(rows) - 1

    def append_log(self, log: models.LogEntry) -> None:
        self.client.append_row("紀錄頁面", log.to_row())

    def update_home_status(self, week: int, map_id: str) -> None:
        ws = self.client.worksheet("首頁")
        ws.update(range_name="C2", values=[[week]])
        ws.update(range_name="G2", values=[[map_id]])
        self.client.invalidate_cache("首頁")

    def get_home_status(self) -> Tuple[Optional[int], Optional[str]]:
        rows = self.client.read_rows("首頁")
        if not rows or len(rows) < 2:
            return None, None
        row = rows[1]
        week_value = row[2] if len(row) > 2 else None
        map_value = row[6] if len(row) > 6 else None
        week = None
        if week_value is not None:
            text = str(week_value).strip()
            if text:
                try:
                    week = int(float(text))
                except Exception:
                    week = None
        map_id = str(map_value).strip() if map_value is not None else None
        if map_id == "":
            map_id = None
        return week, map_id

    def get_logs(self, limit: Optional[int] = None) -> Tuple[List[str], List[List[str]]]:
        header, data = self.client.read_rows_with_header("紀錄頁面")
        if limit and limit > 0:
            data = data[-limit:]
        return header, data
