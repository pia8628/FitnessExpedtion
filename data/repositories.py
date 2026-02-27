"""
Repository layer mapping worksheets to typed records.

Each function should only contain mapping/parsing logic and delegate IO to SheetsClient.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from data.sheets_client import SheetsClient
from domain import models
from gspread.utils import rowcol_to_a1

JOB_ALIAS_MAP = {
    "弓箭手": "Ar",
    "法師": "Ma",
    "牧師": "Pr",
    "劍士": "Sw",
    "盜賊": "Th",
    "通用": "Ge",
}


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


def _normalize_job_token(token: str) -> str:
    raw = str(token or "").strip()
    if not raw:
        return ""
    if len(raw) >= 2:
        prefix = raw[:2].upper()
        if prefix in {"AR", "MA", "PR", "SW", "TH", "GE"}:
            return prefix.title()
    if raw in JOB_ALIAS_MAP:
        return JOB_ALIAS_MAP[raw]
    upper = raw.upper()
    if upper in {"AR", "MA", "PR", "SW", "TH", "GE"}:
        return upper.title()
    lower = raw.lower()
    english_alias = {
        "archer": "Ar",
        "mage": "Ma",
        "wizard": "Ma",
        "priest": "Pr",
        "cleric": "Pr",
        "swordsman": "Sw",
        "warrior": "Sw",
        "thief": "Th",
        "rogue": "Th",
        "general": "Ge",
    }
    if lower in english_alias:
        return english_alias[lower]
    return raw


def _skill_prefix(skill_id: str) -> str:
    sid = str(skill_id or "").strip()
    if len(sid) < 2:
        return ""
    prefix = sid[:2].upper()
    if prefix in {"AR", "MA", "PR", "SW", "TH", "GE"}:
        return prefix.title()
    return ""


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
        col_job = _col_index_any(header, ["職業代碼", "職業", "職業ID"], default=-1)
        col_skill = _col_index_any(header, ["技能ID", "技能編碼", "技能代碼"], default=-1)
        col_name = _col_index_any(header, ["技能名稱", "名稱"], default=-1)
        col_kind = _col_index_any(header, ["主被動"], default=-1)
        col_mp = _col_index_any(header, ["MP消耗", "消耗MP"], default=-1)
        col_total = _col_index_any(header, ["每週可用總次數", "每週可用次數"], default=-1)
        col_reset = _col_index_any(header, ["重置規則"], default=-1)
        col_desc = _col_index_any(header, ["技能效果說明", "技能敘述", "技能描述", "敘述"], default=-1)
        col_enabled = _col_index_any(header, ["啟用狀態"], default=-1)
        results: List[models.SkillState] = []
        target_job = _normalize_job_token(job_code)
        for row in data:
            # Parse with header mapping.
            h_job = str(row[col_job]).strip() if 0 <= col_job < len(row) else ""
            h_skill = str(row[col_skill]).strip() if 0 <= col_skill < len(row) else ""
            h_name = str(row[col_name]).strip() if 0 <= col_name < len(row) else ""
            h_kind = str(row[col_kind]).strip() if 0 <= col_kind < len(row) else ""
            h_mp = str(row[col_mp]).strip() if 0 <= col_mp < len(row) else ""
            h_total = str(row[col_total]).strip() if 0 <= col_total < len(row) else ""
            h_reset = str(row[col_reset]).strip() if 0 <= col_reset < len(row) else ""
            h_desc = str(row[col_desc]).strip() if 0 <= col_desc < len(row) else ""
            h_enabled = str(row[col_enabled]).strip() if 0 <= col_enabled < len(row) else ""

            # Parse with positional fallback A~I.
            p_skill = str(row[0]).strip() if len(row) > 0 else ""
            p_job = str(row[1]).strip() if len(row) > 1 else ""
            p_name = str(row[2]).strip() if len(row) > 2 else ""
            p_kind = str(row[3]).strip() if len(row) > 3 else ""
            p_mp = str(row[4]).strip() if len(row) > 4 else ""
            p_total = str(row[6]).strip() if len(row) > 6 else ""
            p_reset = str(row[7]).strip() if len(row) > 7 else ""
            p_desc = str(row[8]).strip() if len(row) > 8 else ""

            h_job_norm = _normalize_job_token(h_job)
            p_job_norm = _normalize_job_token(p_job)
            use_positional = (p_job_norm == target_job) and (h_job_norm != target_job or not h_skill)
            row_job = p_job_norm if use_positional else h_job_norm
            skill_id_for_match = p_skill if use_positional else h_skill
            if not skill_id_for_match:
                skill_id_for_match = p_skill or h_skill
            match_by_skill_prefix = _skill_prefix(skill_id_for_match) == target_job
            if row_job != target_job and not match_by_skill_prefix:
                continue
            if row_job != target_job and match_by_skill_prefix and p_skill:
                use_positional = True

            skill_id = p_skill if use_positional else h_skill
            if not skill_id:
                skill_id = p_skill
            if not skill_id:
                continue

            name = (p_name if use_positional else h_name) or p_name
            kind = (p_kind if use_positional else h_kind) or p_kind
            mp_text = (p_mp if use_positional else h_mp) or p_mp or "0"
            total_text = (p_total if use_positional else h_total) or p_total
            reset_rule = (p_reset if use_positional else h_reset) or p_reset
            desc = (p_desc if use_positional else h_desc) or p_desc
            enabled = h_enabled or "Y"
            try:
                mp_cost = int(float(mp_text or 0))
            except Exception:
                mp_cost = 0
            try:
                total_uses = int(float(total_text))
            except Exception:
                total_uses = None
            if desc.startswith("#ERROR"):
                desc = ""
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

    def add_skill_state(self, state: models.SkillState) -> bool:
        header, _ = self.client.read_rows_with_header("技能狀態")
        if not header:
            return False
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
        return True

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

    def _find_task_row_indices(self, header: List[str], data: List[List[str]], task: models.Task) -> List[int]:
        id_col = _col_index_any(header, ["怪物ID", "怪物編號", "怪物編碼"], default=-1)
        if id_col < 0:
            return []
        matches = []
        for idx, row in enumerate(data, start=2):
            if len(row) <= id_col:
                continue
            if str(row[id_col]).strip() == str(task.monster_id).strip():
                matches.append(idx)
        if not matches:
            return []
        if len(matches) == 1:
            return matches
        player_col = _col_index_any(header, ["玩家"], default=-1)
        start_col = _col_index_any(header, ["開始日"], default=-1)
        deadline_col = _col_index_any(header, ["截止日"], default=-1)
        name_col = _col_index_any(header, ["怪物名稱", "任務名稱", "名稱"], default=-1)
        status_col = _col_index_any(header, ["狀態"], default=-1)

        def _cell(row: List[str], col: int) -> str:
            if col < 0 or col >= len(row):
                return ""
            return str(row[col]).strip()

        def _score(row: List[str]) -> int:
            score = 0
            if str(task.player or "").strip() and _cell(row, player_col) == str(task.player).strip():
                score += 8
            if str(task.start_date or "").strip() and _cell(row, start_col) == str(task.start_date).strip():
                score += 6
            if str(task.deadline or "").strip() and _cell(row, deadline_col) == str(task.deadline).strip():
                score += 6
            if str(task.name or "").strip() and _cell(row, name_col) == str(task.name).strip():
                score += 4
            status_text = _cell(row, status_col)
            if "進行中" in status_text:
                score += 2
            return score

        best_idx = matches[0]
        best_score = -1
        for idx in matches:
            row = data[idx - 2] if idx - 2 < len(data) else []
            s = _score(row)
            if s > best_score or (s == best_score and idx > best_idx):
                best_idx = idx
                best_score = s
        return [best_idx]

    def _find_task_row_idx(self, header: List[str], data: List[List[str]], task: models.Task) -> Optional[int]:
        indices = self._find_task_row_indices(header, data, task)
        return indices[0] if indices else None

    def update_task_status(self, task: models.Task) -> bool:
        header, data = self.client.read_rows_with_header("任務列表")
        row_indices = self._find_task_row_indices(header, data, task)
        if not row_indices:
            row_indices = self._find_task_row_indices_relaxed(header, data, task)
        if not row_indices:
            return False
        is_terminal = str(task.status).startswith("擊殺") or str(task.status).startswith("失敗")
        targets = [row_indices[0]]
        if is_terminal:
            id_col = _col_index_any(header, ["怪物ID", "怪物編號", "怪物編碼"], default=-1)
            player_col = _col_index_any(header, ["玩家"], default=-1)
            start_col = _col_index_any(header, ["開始日"], default=-1)
            deadline_col = _col_index_any(header, ["截止日"], default=-1)
            if id_col >= 0:
                def _cell(row: List[str], col: int) -> str:
                    if col < 0 or col >= len(row):
                        return ""
                    return str(row[col]).strip()
                monster = str(task.monster_id or "").strip()
                player = str(task.player or "").strip()
                start = str(task.start_date or "").strip()
                deadline = str(task.deadline or "").strip()
                all_matches: List[int] = []
                for idx, src in enumerate(data, start=2):
                    if _cell(src, id_col) != monster:
                        continue
                    if player and _cell(src, player_col) != player:
                        continue
                    if start and _cell(src, start_col) != start:
                        continue
                    if deadline and _cell(src, deadline_col) != deadline:
                        continue
                    all_matches.append(idx)
                if all_matches:
                    targets = all_matches
        for row_idx in targets:
            existing = data[row_idx - 2] if row_idx - 2 < len(data) else []
            row = existing + ["" for _ in range(len(header) - len(existing))]
            before_row = list(row)
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
            # Hard fallback: if status header cannot be matched, write by positional index.
            status_col = _col_index_any(header, ["狀態", "狀態(?/??/??)"], default=-1)
            if status_col < 0:
                status_col = 10 if len(row) > 10 else max(0, len(row) - 1)
            if status_col >= len(row):
                row.extend([""] * (status_col - len(row) + 1))
            if row[status_col] != task.status:
                row[status_col] = task.status
            # If nothing changed due header mismatch, force-set core identifiers by position.
            if row == before_row and len(row) >= 3:
                row[0] = task.monster_id
                row[1] = task.player
                row[2] = task.name
                row[status_col] = task.status
            self.client.update_row("任務列表", row_idx, row)
        return True

    def _find_task_row_indices_relaxed(
        self, header: List[str], data: List[List[str]], task: models.Task
    ) -> List[int]:
        """Fallback matcher for legacy/misaligned headers."""
        player_col = _col_index_any(header, ["玩家"], default=-1)
        name_col = _col_index_any(header, ["怪物名稱", "任務名稱", "名稱"], default=-1)
        status_col = _col_index_any(header, ["狀態"], default=-1)
        if player_col < 0:
            player_col = 1
        if name_col < 0:
            name_col = 2
        if status_col < 0:
            status_col = 10

        def _cell(row: List[str], col: int) -> str:
            if col < 0 or col >= len(row):
                return ""
            return str(row[col]).strip()

        player = str(task.player or "").strip()
        name = str(task.name or "").strip()
        matches: List[int] = []
        for idx, row in enumerate(data, start=2):
            if player and _cell(row, player_col) != player:
                continue
            if name and _cell(row, name_col) != name:
                continue
            status = _cell(row, status_col)
            # Prefer rows still in progress.
            if status and ("擊殺" in status or "失敗" in status):
                continue
            matches.append(idx)
        return matches

    def delete_task(
        self,
        monster_id: str,
        player: Optional[str] = None,
        start_date: Optional[str] = None,
        deadline: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        header, data = self.client.read_rows_with_header("任務列表")
        if not header:
            return False
        dummy_task = models.Task(
            monster_id=monster_id,
            player=player or "",
            name=name or "",
            difficulty="",
            content="",
            start_date=start_date,
            deadline=deadline,
            status="",
        )
        row_idx = self._find_task_row_idx(header, data, dummy_task)
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
