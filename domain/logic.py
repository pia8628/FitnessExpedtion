"""
Core business logic orchestrating Sheet repositories, events, skills, and logging.

Functions here should be side-effect free except for calls into repositories.
"""

from __future__ import annotations

import datetime
import random
from typing import List, Optional

from data.repositories import Repositories
from domain import effects, models, skills
from utils import time as time_utils
from utils import validators

TASK_EVENT_CODES = {
    "IF_OUTDOOR_PHOTO_THEN_EXP+2",
    "IF_OUTDOOR_EXERCISE_THEN_EXP+2",
    "EXTRA_WORKOUT_MVP_EXP+5",
    "FIRST_EXERCISE_EXP=1",
}

DEFERRED_EVENT_CODES = {
    "CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5",
}


class Logic:
    """核心業務邏輯類，負責協調玩家狀態、任務、技能和事件系統的所有操作。"""
    
    def __init__(self, repo: Repositories) -> None:
        """初始化 Logic 實例。
        
        Args:
            repo: 資料庫儲存庫，負責與 Google Sheets 的互動
        """
        self.repo = repo  # 資料層引用
        self.players: List[models.PlayerState] = []  # 當前內存中的玩家狀態列表
        self.tasks: List[models.Task] = []  # 當前內存中的任務列表
        self.skill_states: List[models.SkillState] = []  # 當前內存中的技能狀態列表

    def refresh_state(self):
        """從資料庫同步所有必要的狀態數據到內存。
        
        用於確保在執行操作前，內存中的數據是最新的。
        
        Returns:
            self: 便於方法鏈式調用
        """
        self.players = self.repo.get_player_states()  # 從 Sheets 載入所有玩家
        self.tasks = self.repo.get_tasks()  # 從 Sheets 載入所有任務
        self.skill_states = self.repo.get_skill_states()  # 從 Sheets 載入所有技能狀態
        return self

    def create_new_game(self, players: List[tuple[str, str]]) -> tuple[bool, str]:
        """建立新遊戲並初始化資料。"""
        if not players:
            return False, "缺少玩家資料。"
        if len(players) > 5:
            return False, "玩家人數不可超過 5 位。"
        cleaned = [(name.strip(), job.strip()) for name, job in players]
        if any(not name for name, _ in cleaned) or any(not job for _, job in cleaned):
            return False, "玩家名稱或職業不可為空。"
        if len({name for name, _ in cleaned}) != len(cleaned):
            return False, "玩家名稱不可重複。"

        # 清空任務與紀錄
        self.repo.clear_sheet_data("任務列表")
        self.repo.clear_sheet_data("紀錄頁面")

        # 初始化玩家狀態
        levels, hp_inc, mp_inc, _ = self.repo.get_level_table()
        base_level = 1
        level_idx = 0
        if levels:
            if 1 in levels:
                level_idx = levels.index(1)
            base_level = levels[level_idx]
        states = []
        for name, job in cleaned:
            job_base_hp, job_base_mp = self.repo.get_job_base_stats(job)
            hp_bonus = hp_inc[level_idx] if level_idx < len(hp_inc) else 0
            mp_bonus = mp_inc[level_idx] if level_idx < len(mp_inc) else 0
            max_hp = job_base_hp + hp_bonus
            max_mp = job_base_mp + mp_bonus
            states.append(
                models.PlayerState(
                    name=name,
                    job=job,
                    level=base_level,
                    exp=0,
                    hp_current=max_hp,
                    mp_current=max_mp,
                    hp_max=max_hp,
                    mp_max=max_mp,
                    skill_summary="",
                )
            )
        self.repo.replace_player_states(states)

        # 初始化首頁週數與地圖
        maps = self.repo.get_maps()
        map_id = min(maps, key=lambda m: m.week).map_id if maps else ""
        self.repo.update_home_status(1, map_id)

        # 初始化技能
        skill_defs = {}
        for job_code, _ in cleaned:
            for skill in self.repo.get_job_skill_pool(job_code):
                skill_defs[skill.skill_id] = skill
        skill_states: List[models.SkillState] = []
        for player in states:
            base_skill_ids = ["GeA001", "GeA002"]
            job_skills = self.repo.get_job_skill_pool(player.job)
            job_skill_ids = {s.skill_id for s in job_skills}
            owned = set()
            for skill_id in base_skill_ids:
                tmpl = skill_defs.get(skill_id) or self.repo.get_skill_definition(skill_id)
                if not tmpl:
                    tmpl = models.SkillState(
                        player="",
                        job=player.job,
                        skill_id=skill_id,
                        name=skill_id,
                        kind="主動",
                        mp_cost=0,
                        enabled="Y",
                        total_uses=None,
                        remaining=None,
                        reset_rule="",
                        description="",
                    )
                skill_states.append(
                    models.SkillState(
                        player=player.name,
                        job=player.job,
                        skill_id=tmpl.skill_id,
                        name=tmpl.name,
                        kind=tmpl.kind,
                        mp_cost=tmpl.mp_cost,
                        enabled="Y",
                        total_uses=tmpl.total_uses,
                        remaining=tmpl.total_uses,
                        reset_rule=tmpl.reset_rule,
                        description=tmpl.description,
                    )
                )
                owned.add(skill_id)
            for skill in job_skills:
                if skill.skill_id in owned:
                    continue
                skill_states.append(
                    models.SkillState(
                        player=player.name,
                        job=player.job,
                        skill_id=skill.skill_id,
                        name=skill.name,
                        kind=skill.kind,
                        mp_cost=skill.mp_cost,
                        enabled="N",
                        total_uses=skill.total_uses,
                        remaining=skill.total_uses,
                        reset_rule=skill.reset_rule,
                        description=skill.description,
                    )
                )
        if skill_states:
            self.repo.replace_skill_states(skill_states)

        # 重置技能次數
        self.refresh_state()
        self.reset_weekly_skills()
        self.refresh_state()

        return True, "已建立新遊戲並初始化狀態。"

    def classify_event_kind(self, event: models.Event) -> str:
        category = (event.category or "").strip().lower()
        if "任務" in category or "task" in category:
            return "task"
        if "被動" in category or "passive" in category:
            return "passive"
        codes = self.parse_event_codes(event.effect_code or "")
        if any(code in TASK_EVENT_CODES for code in codes):
            return "task"
        return "passive"

    def is_task_event(self, event: Optional[models.Event]) -> bool:
        if not event:
            return False
        return self.classify_event_kind(event) == "task"

    def _split_event_codes(self, codes: List[str]) -> tuple[List[str], List[str]]:
        task_codes = [c for c in codes if c in TASK_EVENT_CODES]
        passive_codes = [c for c in codes if c not in TASK_EVENT_CODES]
        return task_codes, passive_codes

    def parse_event_codes(self, effect_code: str) -> List[str]:
        if not effect_code:
            return []
        normalized = effect_code.replace(";", ",")
        return [c.strip() for c in normalized.split(",") if c.strip()]

    def apply_event_codes(self, codes: List[str], flags: Optional[dict] = None) -> None:
        """應用事件代碼的效果到玩家和任務，並持久化結果。
        
        Args:
            codes: 事件代碼列表（如 ['IF_OUTDOOR_EXERCISE_THEN_EXP+2']）
            flags: 可選的額外上下文標誌，用於傳遞事件特定的參數
        
        流程:
            1. 構建包含玩家和任務的上下文
            2. 遍歷每個事件代碼並分發到對應的效果處理器
            3. 將修改後的玩家和任務保存回資料庫
        """
        context = {"players": self.players, "tasks": self.tasks}  # 建立執行上下文
        if flags:
            context.update(flags)  # 加入額外標誌
        for code in codes:
            handler = effects.dispatch(code)  # 根據代碼獲取對應的效果處理函數
            handler(context)  # 執行效果處理
        # 將所有修改持久化回資料庫（批次更新玩家，避免寫入配額超限）
        players = context.get("players", [])
        for player in players:
            if getattr(player, "penalty_weeks", 0) > 0:
                player.mp_current = 0
        if players:
            self.repo.update_player_states_bulk(players)
        for task in context.get("tasks", []):
            self.repo.update_task_status(task)

    def get_event_for_week(self, week: int) -> Optional[models.Event]:
        """根據週數從日誌中查詢該週抽取的事件。
        
        Args:
            week: 週數
            
        Returns:
            該週的事件物件，若未找到或無日誌則返回 None
            
        流程:
            1. 從日誌表中搜尋指定週數且類型為 "抽事件" 的記錄
            2. 提取事件代碼
            3. 在事件表中查找對應的完整事件資訊
        """
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return None
        # 定位日誌表中各列的索引
        idx_week = header.index("週數") if "週數" in header else None
        idx_type = header.index("類型") if "類型" in header else None
        idx_code = header.index("代碼") if "代碼" in header else None
        if idx_week is None or idx_type is None or idx_code is None:
            return None
        # 從日誌中倒序查詢該週的事件抽取記錄
        event_id = None
        for row in reversed(data):
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if row[idx_week] != str(week):
                continue
            if row[idx_type] == "抽事件":
                event_id = row[idx_code]
                break
        if not event_id:
            return None
        # 從事件表中查詢對應的事件物件
        events = self.repo.get_events()
        return next((e for e in events if e.event_id == event_id), None)

    def get_last_week_from_logs(self) -> int:
        """從日誌中查詢並返回最後一個已記錄的週數。
        
        Returns:
            最後記錄的週數，若無日誌則返回 0
        """
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return 0
        idx_week = header.index("週數") if "週數" in header else None
        if idx_week is None:
            return 0
        max_week = 0
        # 遍歷所有日誌行，找出最大的週數
        for row in data:
            if len(row) <= idx_week:
                continue
            value = str(row[idx_week]).strip()
            if not value:
                continue
            try:
                week = int(float(value))
            except Exception:
                continue
            max_week = max(max_week, week)
        return max_week

    def get_next_week(self) -> int:
        """計算下一個週數（最後記錄週數 + 1）。
        
        Returns:
            下一週的週數，若無記錄則返回 1
        """
        last_week = self.get_last_week_from_logs()
        return last_week + 1 if last_week > 0 else 1

    def get_next_map(self, current: Optional[models.MapInfo]) -> Optional[models.MapInfo]:
        """根據當前地圖獲取下一個地圖。
        
        Args:
            current: 當前地圖，若為 None 則返回第一個地圖
            
        Returns:
            下一個地圖，若已是最後一個則返回當前地圖，若無地圖則返回 None
        """
        maps = self.repo.get_maps()
        if not maps:
            return None
        maps_sorted = list(maps)
        if current is None:
            return maps_sorted[0]
        current_id = (current.map_id or "").strip()
        for idx, item in enumerate(maps_sorted):
            if (item.map_id or "").strip() == current_id:
                return maps_sorted[idx + 1] if idx + 1 < len(maps_sorted) else item
        for item in maps_sorted:
            if item.week > current.week:
                return item
        return current

    def has_boss_settlement_for_week(self, week: int) -> bool:
        """檢查該週是否已進行過 BOSS 結算。
        
        Args:
            week: 要檢查的週數
            
        Returns:
            True 若該週有 BOSS 結算記錄，否則返回 False
        """
        if week <= 0:
            return False
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return False
        idx_week = header.index("週數") if "週數" in header else None
        idx_type = header.index("類型") if "類型" in header else None
        if idx_week is None or idx_type is None:
            return False
        # 倒序查詢該週的 BOSS 結算記錄
        for row in reversed(data):
            if len(row) <= max(idx_week, idx_type):
                continue
            if row[idx_week] != str(week):
                continue
            if row[idx_type] == "BOSS":
                return True
        return False

    def has_boss_settlement_for_boss(self, boss_id: str, week: Optional[int] = None) -> bool:
        """檢查是否已有指定 BOSS 的結算紀錄。"""
        if not boss_id:
            return False
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return False
        idx_week = header.index("週數") if "週數" in header else None
        idx_type = header.index("類型") if "類型" in header else None
        idx_code = header.index("代碼") if "代碼" in header else None
        if idx_type is None or idx_code is None:
            return False
        week_str = str(week) if week is not None else None
        for row in reversed(data):
            if len(row) <= max(idx_type, idx_code):
                continue
            if row[idx_type] != "BOSS":
                continue
            if row[idx_code] != boss_id:
                continue
            if week_str and idx_week is not None:
                if len(row) <= idx_week:
                    continue
                if str(row[idx_week]).strip() != week_str:
                    continue
            return True
        return False

    def get_boss_settlement_results(self, boss_id: str, week: Optional[int] = None) -> dict:
        """讀取日誌取得 BOSS 結算的每人 EXP 變化。"""
        results = {}
        if not boss_id:
            return results
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return results

        def idx_any(names: List[str]) -> Optional[int]:
            for name in names:
                if name in header:
                    return header.index(name)
            for idx, head in enumerate(header):
                for name in names:
                    if name and name in head:
                        return idx
            return None

        idx_week = idx_any(["週數"])
        idx_type = idx_any(["類型"])
        idx_code = idx_any(["代碼"])
        idx_player = idx_any(["玩家"])
        idx_delta_exp = idx_any(["EXP變化", "EXP變更", "EXP變"])
        if idx_type is None or idx_code is None or idx_player is None or idx_delta_exp is None:
            return results
        week_str = str(week) if week is not None else None
        for row in data:
            if len(row) <= max(idx_type, idx_code, idx_player, idx_delta_exp):
                continue
            if row[idx_type] != "BOSS":
                continue
            if row[idx_code] != boss_id:
                continue
            if week_str and idx_week is not None:
                if len(row) <= idx_week:
                    continue
                if str(row[idx_week]).strip() != week_str:
                    continue
            player = str(row[idx_player]).strip()
            if not player:
                continue
            try:
                exp = int(float(str(row[idx_delta_exp]).strip() or 0))
            except Exception:
                exp = 0
            results[player] = exp
        return results

    def has_map_choice_for_week(self, week: int, map_id: str) -> bool:
        if week <= 0 or not map_id:
            return False
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return False
        idx_week = header.index("週數") if "週數" in header else None
        idx_type = header.index("類型") if "類型" in header else None
        idx_code = header.index("代碼") if "代碼" in header else None
        if idx_week is None or idx_type is None or idx_code is None:
            return False
        week_str = str(week)
        for row in reversed(data):
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if row[idx_week] != week_str:
                continue
            if row[idx_type] != "地圖選擇":
                continue
            if row[idx_code] == map_id:
                return True
        return False

    def apply_boss_map_choice(
        self, map_info: models.MapInfo, boss_week: int, choice: str
    ) -> tuple[bool, str]:
        if not map_info:
            return False, "缺少地圖資訊。"
        if boss_week <= 0:
            return False, "週數無效。"
        choice = choice.upper()
        if choice not in {"NEXT", "REPLAY"}:
            return False, "選項無效。"
        if self.has_map_choice_for_week(boss_week, map_info.map_id):
            return False, "本週已完成地圖選擇。"

        target_map_id = map_info.map_id
        if choice == "NEXT":
            next_map = self.get_next_map(map_info)
            if not next_map or next_map.map_id == map_info.map_id:
                return False, "找不到下一張地圖。"
            target_map_id = next_map.map_id
        self.repo.update_home_status(1, target_map_id)

        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(boss_week),
            player="全員",
            type_="地圖選擇",
            code=map_info.map_id,
            name=map_info.name,
            desc=choice,
            target=target_map_id,
            delta_hp=0,
            delta_mp=0,
            delta_exp=0,
            hp=0,
            mp=0,
            exp=0,
        )
        self.repo.append_log(log)
        if choice == "REPLAY":
            reset_log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=str(boss_week),
                player="全員",
                type_="地圖重置",
                code=map_info.map_id,
                name=map_info.name,
                desc="重置進度",
                target=map_info.map_id,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=0,
                mp=0,
                exp=0,
            )
            self.repo.append_log(reset_log)
        return True, "已完成地圖選擇。"

    def has_drawn_event(self, week: int) -> bool:
        """檢查該週是否已抽取事件。
        
        Args:
            week: 要檢查的週數
            
        Returns:
            True 若該週已抽取事件，否則返回 False
        """
        return self.get_event_for_week(week) is not None

    def has_drawn_monsters(self, week: int) -> bool:
        """檢查該週是否已抽取怪物任務。
        
        Args:
            week: 要檢查的週數
            
        Returns:
            True 若該週已抽取怪物，否則返回 False
        """
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return False
        idx_week = header.index("週數") if "週數" in header else None
        idx_type = header.index("類型") if "類型" in header else None
        if idx_week is None or idx_type is None:
            return False
        # 倒序查詢該週的怪物抽取記錄
        for row in reversed(data):
            if len(row) <= max(idx_week, idx_type):
                continue
            if row[idx_week] != str(week):
                continue
            if row[idx_type] == "抽怪物":
                return True
        return False

    def apply_choice_monster_event(self, week: int, choice: str) -> tuple[bool, str]:
        if week <= 0:
            return False, "週數無效。"
        choice = choice.upper()
        if choice not in {"A", "B"}:
            return False, "選項無效。"
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        if self._has_event_choice(str(week), data, idx):
            return False, "本週已完成選擇。"

        self.refresh_state()
        updated = 0
        for task in self.tasks:
            task_week = self._get_task_week(task, header, data, idx)
            if task_week != str(week):
                continue
            if choice == "A":
                task.difficulty = self._adjust_difficulty(task.difficulty, -1)
            else:
                task.difficulty = self._adjust_difficulty(task.difficulty, 1)
                task.success_exp += 5
            self.repo.update_task_status(task)
            updated += 1

        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(week),
            player="全員",
            type_="事件",
            code="CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5",
            name="選擇事件",
            desc=f"選擇{choice}",
            target="全隊",
            delta_hp=0,
            delta_mp=0,
            delta_exp=0,
            hp=0,
            mp=0,
            exp=0,
        )
        self.repo.append_log(log)
        return True, f"已套用選擇{choice}，更新 {updated} 筆任務。"

    def get_map_progress(self, map_id: str) -> int:
        """獲取指定地圖的完成進度（已完成的步數）。
        
        Args:
            map_id: 地圖 ID
            
        Returns:
            該地圖已完成的步數，若無進度則返回 0
        """
        header, data = self.repo.get_logs(limit=1000)
        if not header:
            return 0
        idx_type = header.index("類型") if "類型" in header else None
        idx_code = header.index("代碼") if "代碼" in header else None
        if idx_type is None or idx_code is None:
            return 0
        reset_index = -1
        for idx, row in enumerate(data):
            if len(row) <= max(idx_type, idx_code):
                continue
            if row[idx_type] != "地圖重置":
                continue
            if row[idx_code] == map_id:
                reset_index = idx
        # 統計該地圖在日誌中的完成次數（重置後）
        count = 0
        for idx, row in enumerate(data):
            if idx <= reset_index:
                continue
            if len(row) <= max(idx_type, idx_code):
                continue
            if row[idx_type] != "地圖":
                continue
            if row[idx_code] == map_id:
                count += 1
        return count

    def is_boss_stage(self, map_info: models.MapInfo) -> bool:
        """判斷該地圖是否已進入 BOSS 階段（進度達到週數）。
        
        Args:
            map_info: 地圖資訊
            
        Returns:
            True 若地圖進度 >= 地圖週數，否則返回 False
        """
        if not map_info or map_info.week <= 0:
            return False
        progress = self.get_map_progress(map_info.map_id)
        return progress >= map_info.week

    def reset_weekly_skills(self) -> int:
        """重置所有啟用的「每週重置」技能的剩餘使用次數。
        
        Returns:
            重置的技能數量
        """
        header, data, skill_states = self.repo.get_skill_states_with_header()
        if not header:
            return 0
        updated = []
        # 遍歷所有技能狀態，找出需要週期重置的技能
        for state in skill_states:
            if not state.enabled or state.enabled.upper() != "Y":
                continue  # 跳過未啟用的技能
            if state.total_uses is None:
                continue
            # 檢查重置規則是否包含「週」
            rule = (state.reset_rule or "").strip()
            if rule and "週" not in rule and "week" not in rule.lower():
                continue
            # 將剩餘次數重置為總使用次數
            state.remaining = state.total_uses
            updated.append(state)
        if not updated:
            return 0
        # 批量保存更新的技能狀態
        return self.repo.update_skill_states_bulk(updated)

    def apply_weekly_penalties(self, week: int) -> int:
        """每週重置時套用死亡懲罰與復活規則。"""
        if week <= 0:
            return 0
        self.refresh_state()
        updated = []
        for player in self.players:
            if player.penalty_weeks <= 0:
                continue
            if player.hp_current <= 0 and player.hp_max > 0:
                player.hp_current = player.hp_max // 2
            player.mp_current = 0
            player.penalty_weeks = max(0, player.penalty_weeks - 1)
            updated.append(player)
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=str(week),
                player=player.name,
                type_="懲罰",
                code="HP_ZERO_PENALTY",
                name="死亡懲罰",
                desc=f"剩餘{player.penalty_weeks}週",
                target=player.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
            self.repo.append_log(log)
        if updated:
            self.repo.update_player_states_bulk(updated)
        return len(updated)

    def complete_outdoor_exercise_event(self, week: int) -> tuple[bool, str]:
        """記錄戶外運動事件並應用效果（每週一次）。
        
        Args:
            week: 週數
            
        Returns:
            (成功布林值, 訊息)
            
        流程:
            1. 驗證週數有效性
            2. 檢查該週是否已完成過此事件
            3. 應用事件代碼效果（全員 EXP +2）
            4. 記錄日誌
        """
        if week <= 0:
            return False, "週數無效。"
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        # 檢查該週是否已完成此事件
        if self._has_event_code(str(week), "IF_OUTDOOR_EXERCISE_THEN_EXP+2", data, idx):
            return False, "本週已完成戶外運動事件。"
        # 應用事件效果
        event_codes = self._get_event_codes_for_week(str(week))
        if "REST_MP_RECOVERY_DISABLED" in event_codes:
            return False, "本週休息回 MP 已被禁用。"
        self.apply_event_codes(["IF_OUTDOOR_EXERCISE_THEN_EXP+2"], {"outdoor_exercise": True})
        # 記錄日誌
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(week),
            player="全員",
            type_="事件",
            code="IF_OUTDOOR_EXERCISE_THEN_EXP+2",
            name="戶外運動",
            desc="完成戶外運動事件，全員 EXP +2",
            target="全員",
            delta_hp=0,
            delta_mp=0,
            delta_exp=0,
            hp=0,
            mp=0,
            exp=0,
        )
        self.repo.append_log(log)
        return True, "已完成戶外運動事件。"

    def complete_outdoor_photo_event(self, week: int) -> tuple[bool, str]:
        """記錄戶外照片事件並應用效果（每週一次）。
        
        Args:
            week: 週數
            
        Returns:
            (成功布林值, 訊息)
            
        流程:
            1. 驗證週數有效性
            2. 檢查該週是否已完成過此事件
            3. 應用事件代碼效果（全員 EXP +2）
            4. 記錄日誌
        """
        if week <= 0:
            return False, "週數無效。"
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        # 檢查該週是否已完成此事件
        if self._has_event_code(str(week), "IF_OUTDOOR_PHOTO_THEN_EXP+2", data, idx):
            return False, "本週已完成戶外照片事件。"
        # 應用事件效果
        event_codes = self._get_event_codes_for_week(str(week))
        if "REST_MP_RECOVERY_DISABLED" in event_codes:
            return False, "本週休息回 MP 已被禁用。"
        self.apply_event_codes(["IF_OUTDOOR_PHOTO_THEN_EXP+2"], {"outdoor_photo": True})
        # 記錄日誌
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(week),
            player="全員",
            type_="事件",
            code="IF_OUTDOOR_PHOTO_THEN_EXP+2",
            name="戶外照片",
            desc="完成戶外照片事件，全員 EXP +2",
            target="全員",
            delta_hp=0,
            delta_mp=0,
            delta_exp=0,
            hp=0,
            mp=0,
            exp=0,
        )
        self.repo.append_log(log)
        return True, "已完成戶外照片事件。"

    def complete_extra_workout_event(self, week: int, player_name: str) -> tuple[bool, str]:
        """
        Record extra workout event; apply EXP +5 to the player once per week.
        """
        if week <= 0:
            return False, "週數無效。"
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        event_codes = self._get_event_codes_for_week(str(week))
        if "EXTRA_WORKOUT_MVP_EXP+5" not in event_codes:
            return False, "本週沒有額外運動事件。"
        if self._has_event_code_for_player(
            str(week), "EXTRA_WORKOUT_MVP_EXP+5", player_name, data, idx
        ):
            return False, "本週已完成額外運動事件。"
        player = self._find_player(player_name)
        if not player:
            return False, "找不到玩家。"
        player.exp += 5
        level_log = self._check_level_up(player)
        self.repo.save_player_state(player)
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(week),
            player=player.name,
            type_="事件",
            code="EXTRA_WORKOUT_MVP_EXP+5",
            name="額外運動",
            desc="完成額外運動事件，個人 EXP +5",
            target=player.name,
            delta_hp=0,
            delta_mp=0,
            delta_exp=5,
            hp=player.hp_current,
            mp=player.mp_current,
            exp=player.exp,
        )
        self.repo.append_log(log)
        if level_log:
            self.repo.append_log(level_log)
        return True, "已完成額外運動事件。"

    def has_event_completion(self, week: int, code: str, player_name: Optional[str] = None) -> bool:
        if week <= 0:
            return False
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return False
        idx = self._log_indices(header)
        week_str = str(week)
        if player_name:
            return self._has_event_code_for_player(week_str, code, player_name, data, idx)
        return self._has_event_code(week_str, code, data, idx)

    def draw_event(self) -> Optional[models.Event]:
        """抽取事件（不綁定特定週數）。
        
        Returns:
            隨機選擇的事件物件
        """
        return self.draw_event_for_week(week=None)

    def draw_event_for_week(self, week: Optional[int]) -> Optional[models.Event]:
        """抽取特定週數的事件，並應用事件效果。
        
        Args:
            week: 週數，若為 None 則不綁定週數
            
        Returns:
            抽取的事件物件
            
        流程:
            1. 若該週已有事件，直接返回已有事件
            2. 從事件表隨機選擇一個事件
            3. 解析並應用事件代碼效果
            4. 記錄日誌
        """
        # 若該週已抽取過事件，直接返回已有事件
        if week is not None and self.has_drawn_event(week):
            return self.get_event_for_week(week)
        # 隨機抽取事件
        events = self.repo.get_events()
        if not events:
            return None
        event = random.choice(events)
        # 解析事件代碼並應用效果（僅被動事件在此套用）
        codes = self.parse_event_codes(event.effect_code)
        if codes:
            _, passive_codes = self._split_event_codes(codes)
            header, data = self.repo.get_logs(limit=500)
            idx = self._log_indices(header)
            to_apply = []
            if week is not None:
                week_str = str(week)
                for code in passive_codes:
                    if code in DEFERRED_EVENT_CODES:
                        continue
                    if self._has_event_code(week_str, code, data, idx):
                        continue
                    to_apply.append(code)
            else:
                to_apply = [c for c in passive_codes if c not in DEFERRED_EVENT_CODES]
            if to_apply:
                self.refresh_state()
                self.apply_event_codes(to_apply)
            if week is not None:
                for code in to_apply:
                    log = models.LogEntry(
                        date=time_utils.now().date().isoformat(),
                        week=str(week),
                        player="全員",
                        type_="事件",
                        code=code,
                        name=event.name,
                        desc=f"{code} {event.description}".strip(),
                        target="全隊",
                        delta_hp=0,
                        delta_mp=0,
                        delta_exp=0,
                        hp=0,
                        mp=0,
                        exp=0,
                    )
                    self.repo.append_log(log)
        # 記錄日誌
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=str(week) if week is not None else "",
            player="全員",
            type_="抽事件",
            code=event.event_id,
            name=event.name,
            desc=f"{event.effect_code} {event.description}".strip(),
            target="全隊",
            delta_hp=0,
            delta_mp=0,
            delta_exp=0,
            hp=0,
            mp=0,
            exp=0,
        )
        self.repo.append_log(log)
        return event

    def cleanup_previous_week_tasks(self, current_week: int) -> int:
        """在週結算時自動失敗上週未完成的任務。
        
        Args:
            current_week: 當前週數
            
        Returns:
            被失敗的任務數量
            
        流程:
            1. 找出上週（current_week - 1）的所有未完成任務
            2. 對每個任務呼叫 fail_task() 自動失敗
            3. 返回失敗的任務數量
        """
        if current_week <= 1:
            return 0
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        target_week = str(current_week - 1)
        status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}  # 已完成或已失敗的狀態
        to_fail = []
        # 搜尋上週未完成的任務
        for task in self.tasks:
            if task.status in status_done:
                continue  # 跳過已完成/失敗的任務
            task_week = self._get_task_week(task, header, data, idx)
            if task_week == target_week:
                player = self._find_player(task.player)
                if player:
                    to_fail.append((task, player))
        # 自動失敗這些任務
        for task, player in to_fail:
            self.fail_task(task, player)
        return len(to_fail)

    def purge_completed_tasks_before_week(self, current_week: int) -> int:
        if current_week <= 1:
            return 0
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        removed = 0
        for task in list(self.tasks):
            if task.status not in {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}:
                continue
            task_week = self._get_task_week(task, header, data, idx)
            if not task_week:
                continue
            try:
                week_int = int(float(str(task_week).strip()))
            except Exception:
                continue
            if week_int < current_week:
                if self.repo.delete_task(task.monster_id):
                    removed += 1
        if removed:
            self.tasks = self.repo.get_tasks()
        return removed

    def draw_monsters(self) -> List[models.Task]:
        """抽取怪物任務（使用最新地圖）。
        
        Returns:
            新建立的怪物任務列表
        """
        maps = self.repo.get_maps()
        if not maps:
            return []
        # 選擇週數最高的地圖
        latest = max(maps, key=lambda m: m.week)
        return self.draw_monsters_for_map(latest, week=latest.week)

    def draw_monsters_for_map(self, map_info: models.MapInfo, week: Optional[int]) -> List[models.Task]:
        """根據地圖資訊為每個未有進行中任務的玩家抽取怪物任務。
        
        Args:
            map_info: 地圖資訊（包含難度比例設定）
            week: 週數
            
        Returns:
            新建立的任務列表
            
        流程:
            1. 建立難度層級的怪物池（易/中/難）
            2. 根據地圖設定的難度權重隨機選擇
            3. 為沒有進行中任務的玩家建立新任務
            4. 設定任務截止日期（基於怪物的時間限制）
            5. 記錄日誌
        """
        monsters = self.repo.get_monsters()
        if not monsters:
            return []
        self.refresh_state()
        event_codes = []
        if week is not None:
            event_codes = self._get_event_codes_for_week(str(week))
        status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}  # 已完成或已失敗的任務狀態
        # 找出所有有進行中任務的玩家（僅計入本週任務）
        active_players = set()
        if week is not None:
            header, data = self.repo.get_logs(limit=500)
            idx = self._log_indices(header)
            for t in self.tasks:
                if t.status and t.status in status_done:
                    continue
                task_week = self._get_task_week(t, header, data, idx)
                if task_week == str(week):
                    active_players.add(t.player)
        else:
            active_players = {
                t.player for t in self.tasks if t.status and t.status not in status_done
            }
        # 按難度分類怪物
        easy_pool = [m for m in monsters if "易" in m.difficulty]
        medium_pool = [m for m in monsters if "中" in m.difficulty]
        hard_pool = [m for m in monsters if "難" in m.difficulty]
        created: List[models.Task] = []
        today = time_utils.now().date()
        count = map_info.difficulty_count if map_info.difficulty_count > 0 else 1  # 每個玩家抽取的怪物數
        # 地圖的難度權重
        weights = [map_info.easy_rate, map_info.medium_rate, map_info.hard_rate]
        if sum(weights) <= 0:
            weights = [1.0, 0.0, 0.0]  # 預設為全易
        
        bump_difficulty = "ALL_MONSTER_LV+1" in event_codes
        minus_one_day = "MONSTER_TIME-1_DAY" in event_codes
        redraw_all = "REDRAW_ALL_MONSTERS" in event_codes

        def pick_monster_for(difficulty: str) -> models.Monster:
            pool = easy_pool if difficulty == "易" else medium_pool if difficulty == "中" else hard_pool
            if not pool:
                pool = monsters  # 若該難度池為空，使用全部怪物
            return random.choice(pool)

        def bump(diff: str) -> str:
            if diff == "易":
                return "中"
            if diff == "中":
                return "難"
            return diff

        def build_assignments() -> List[tuple[models.PlayerState, models.Monster, int]]:
            assignments: List[tuple[models.PlayerState, models.Monster, int]] = []
            for player in self.players:
                if player.name in active_players:
                    continue  # 跳過已有進行中任務的玩家
                for _ in range(count):
                    base_diff = random.choices(["易", "中", "難"], weights=weights, k=1)[0]
                    diff = bump(base_diff) if bump_difficulty else base_diff
                    monster = pick_monster_for(diff)
                    time_limit_days = monster.time_limit_days
                    if minus_one_day and time_limit_days:
                        time_limit_days = max(1, time_limit_days - 1)
                    assignments.append((player, monster, time_limit_days or 0))
            return assignments

        assignments = build_assignments()
        if redraw_all:
            assignments = build_assignments()

        # 為每個沒有進行中任務的玩家建立怪物任務
        for player, monster, time_limit_days in assignments:
            # 計算任務截止日期
            deadline = (
                today + datetime.timedelta(days=time_limit_days)
                if time_limit_days
                else today
            )
            # 建立新任務
            task = models.Task(
                monster_id=monster.monster_id,
                player=player.name,
                name=monster.name,
                difficulty=monster.difficulty,
                content=monster.content,
                start_date=today.isoformat(),
                deadline=deadline.isoformat(),
                status="??進行中",  # 進行中的任務
                success_exp=monster.success_exp,
                fail_hp=-abs(monster.fail_hp),
                time_limit_days=time_limit_days or monster.time_limit_days,
            )
            self.repo.add_task(task)
            created.append(task)
            # 記錄日誌
            log = models.LogEntry(
                date=today.isoformat(),
                week=str(week) if week is not None else "",
                player=player.name,
                type_="抽怪物",
                code=monster.monster_id,
                name=monster.name,
                desc=monster.content,
                target=player.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
            self.repo.append_log(log)
        if created:
            self.tasks = self.repo.get_tasks()
        return created

    def settle_week(
        self, week: int, map_info: models.MapInfo
    ) -> tuple[bool, str, dict]:
        """週結算：清理上週任務、重置技能、抽取事件和怪物。
        
        Args:
            week: 要結算的週數
            map_info: 當前地圖資訊
            
        Returns:
            (成功布林值, 訊息, 詳細字典)
            
        流程:
            1. 驗證週數和地圖狀態
            2. 檢查該週是否已結算（避免重複）
            3. 清理上週未完成的任務（自動失敗）
            4. 重置週期技能
            5. 抽取該週的事件
            6. 為每個無任務的玩家抽取怪物
            7. 更新地圖進度
            8. 檢查是否進入 BOSS 階段
            9. 更新首頁狀態（當前週數和地圖）
        """
        if week <= 0:
            return False, "週數無效。", {}
        # 若地圖已進入 BOSS 階段，需先完成 BOSS 結算才可進入下一週
        if map_info and self.is_boss_stage(map_info):
            home_week, _ = self.repo.get_home_status()
            boss_week = home_week if home_week and home_week > 0 else self.get_last_week_from_logs()
            settled = self.has_boss_settlement_for_week(boss_week)
            if not settled and map_info.boss_id:
                settled = self.has_boss_settlement_for_boss(map_info.boss_id, boss_week)
            if not settled:
                return False, "地圖已進入 BOSS 階段，請先完成 BOSS 結算。", {}
            if not self.has_map_choice_for_week(boss_week, map_info.map_id):
                return False, "請先完成地圖選擇後再進行每週結算。", {}
        # 檢查該週是否已結算
        already_event = self.has_drawn_event(week)
        already_monsters = self.has_drawn_monsters(week)
        if already_event and already_monsters:
            return False, "本週已完成抽卡。", {}
        
        # 執行週結算的各個步驟
        progress_before = self.get_map_progress(map_info.map_id) if map_info else 0
        boss_week_start = (
            map_info is not None
            and map_info.week > 0
            and progress_before + 1 >= map_info.week
        )

        cleared = self.cleanup_previous_week_tasks(week)  # 清理上週任務
        self.purge_completed_tasks_before_week(week)
        penalty_count = self.apply_weekly_penalties(week)  # 懲罰倒數與復活
        reset_count = self.reset_weekly_skills()  # 重置技能
        event = self.draw_event_for_week(week)  # 抽取事件
        created = []
        if not boss_week_start:
            created = self.draw_monsters_for_map(map_info, week=week)  # 抽取怪物
        
        # 更新地圖進度
        progress = 0
        if map_info:
            progress = progress_before + 1
            map_log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=str(week),
                player="全員",
                type_="地圖",
                code=map_info.map_id,
                name=map_info.name,
                desc=f"地圖進度 {progress}/{map_info.week}",
                target=map_info.map_id,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=0,
                mp=0,
                exp=0,
            )
            self.repo.append_log(map_log)
        
        # 更新首頁狀態
        self.repo.update_home_status(week, map_info.map_id)
        
        # 準備返回數據
        detail = {
            "cleared": cleared,  # 被清理的任務數
            "penalty": penalty_count,
            "reset": reset_count,  # 被重置的技能數
            "event": event,  # 抽取的事件
            "tasks": created,  # 新建立的任務列表
            "map_progress": progress,  # 地圖進度
        }
        
        # 構建訊息
        message = (
            f"已結算本週：清除上週任務 {cleared} 筆、懲罰處理 {penalty_count} 位、"
            f"重置技能 {reset_count} 筆，事件/怪物抽卡完成。"
        )
        # 檢查是否進入 BOSS 階段
        if map_info and map_info.week > 0 and progress >= map_info.week:
            message = f"{message} 地圖已進入 BOSS 階段。"
        
        return True, message, detail

    def complete_task(self, task: models.Task, player: models.PlayerState) -> None:
        """標記任務完成，應用獎勵、觸發被動技能並記錄。
        
        Args:
            task: 要完成的任務
            player: 完成任務的玩家
            
        流程:
            1. 計算基礎 EXP 和額外獎勵
            2. 應用事件效果加成（如 FIRST_EXERCISE_EXP、BONUS_EXP+3）
            3. 應用玩家被動技能加成（如 MaP001、ThP001 等）
            4. 檢查等級提升
            5. 更新玩家狀態並記錄日誌
            6. 刪除任務並應用共感回饋機制
            
        TODO:
        - 套用事件/被動影響的 EXP/MP/HP 修正
        - 判定升級並回滿
        - 合體技/特殊狀態處理
        """
        self.refresh_state()
        log_header, log_data = self.repo.get_logs(limit=500)
        log_idx = self._log_indices(log_header)
        week = self._get_task_week(task, log_header, log_data, log_idx)
        week_str = week if week else ""
        event_codes = self._get_event_codes_for_week(week)
        base_exp = task.success_exp
        bonus_exp = 0
        bonus_mp = 0
        today = time_utils.now().date()

        first_exercise_log = False
        if "FIRST_EXERCISE_EXP=1" in event_codes:
            if not self._has_event_code(week_str, "FIRST_EXERCISE_EXP=1", log_data, log_idx):
                base_exp = 1
                first_exercise_log = True

        if "BONUS_EXP+3" in event_codes:
            bonus_exp += 3

        combo_skill_bonus = False
        if self._has_recent_skill_after_last_completion(
            player.name, week_str, {"GeA002"}, log_data, log_idx
        ):
            bonus_exp += 2
            combo_skill_bonus = True

        combo_bonus_log = False
        if "IF_TEAM_COMBO_THEN_ALL_EXP+3" in event_codes:
            if self._team_combo_used(week_str, log_data, log_idx):
                if not self._has_event_bonus_log(
                    player.name, week_str, "IF_TEAM_COMBO_THEN_ALL_EXP+3", log_data, log_idx
                ):
                    bonus_exp += 3
                    combo_bonus_log = True

        passive_ctx = skills.SkillContext(
            actor=player,
            task=task,
            state=self,
            week_str=week_str,
            log_data=log_data,
            log_idx=log_idx,
            today=today,
        )
        passive_result = skills.apply_passive("on_complete", passive_ctx)
        bonus_exp += passive_result.get("bonus_exp", 0)
        bonus_mp += passive_result.get("bonus_mp", 0)
        support_result = skills.apply_passive("on_supported_complete", passive_ctx)
        bonus_exp += support_result.get("bonus_exp", 0)
        support_bonus = support_result.get("support_bonus", False)

        task.status = "?擊殺"
        total_exp = base_exp + bonus_exp
        player.exp += total_exp
        if bonus_mp:
            player.mp_current = validators.clamp(
                player.mp_current + bonus_mp, 0, player.mp_max
            )
        level_log = self._check_level_up(player)
        self._persist_task_and_player(
            task,
            player,
            delta_hp=0,
            delta_mp=bonus_mp,
            delta_exp=total_exp,
            desc="擊敗怪物",
            week=week_str,
            update_task=True,
        )
        if combo_skill_bonus:
            self.repo.append_log(
                models.LogEntry(
                    date=time_utils.now().date().isoformat(),
                    week=week_str,
                    player=player.name,
                    type_="技能",
                    code="GeA002_BONUS",
                    name="合體技",
                    desc="合體技加成 EXP +2",
                    target=player.name,
                    delta_hp=0,
                    delta_mp=0,
                    delta_exp=2,
                    hp=player.hp_current,
                    mp=player.mp_current,
                    exp=player.exp,
                )
            )
        if level_log:
            self.repo.append_log(level_log)

        if combo_bonus_log:
            self._append_event_bonus_log(
                player_state=player,
                week=week_str,
                code="IF_TEAM_COMBO_THEN_ALL_EXP+3",
                delta_exp=3,
            )
        if first_exercise_log:
            self._append_event_bonus_log(
                player_state=player,
                week=week_str,
                code="FIRST_EXERCISE_EXP=1",
                delta_exp=base_exp,
            )
        if support_bonus:
            self._append_event_bonus_log(
                player_state=player,
                week=week_str,
                code="PrP001_BONUS",
                delta_exp=1,
            )
        rescue_ctx = skills.SkillContext(
            actor=player,
            state=self,
            week_str=week_str,
            log_data=log_data,
            log_idx=log_idx,
            players=self.players,
            completed_player=player,
        )
        rescue_result = skills.apply_passive("on_rescued_complete", rescue_ctx)
        for rescuer_name, delta_mp, target_name in rescue_result.get("rescues", []):
            rescuer = self._find_player(rescuer_name)
            if not rescuer:
                continue
            rescuer.mp_current = validators.clamp(
                rescuer.mp_current + delta_mp, 0, rescuer.mp_max
            )
            if rescuer.penalty_weeks > 0:
                rescuer.mp_current = 0
            self.repo.save_player_state(rescuer)
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=week_str,
                player=rescuer.name,
                type_="事件",
                code="PrP002",
                name="共感回饋",
                desc="救援回饋",
                target=target_name,
                delta_hp=0,
                delta_mp=delta_mp,
                delta_exp=0,
                hp=rescuer.hp_current,
                mp=rescuer.mp_current,
                exp=rescuer.exp,
            )
            self.repo.append_log(log)

    def fail_task(self, task: models.Task, player: models.PlayerState) -> None:
        """標記任務失敗，應用懲罰並記錄。
        
        Args:
            task: 失敗的任務
            player: 失敗任務的玩家
            
        流程:
            1. 標記任務狀態為失敗
            2. 計算 HP 扣除量（基礎傷害）
            3. 應用保護盾被動（如 SwP001、SwP002）減少傷害
            4. 更新玩家 HP 並記錄日誌
            5. 刪除任務
        """
        self.refresh_state()
        log_header, log_data = self.repo.get_logs(limit=500)
        log_idx = self._log_indices(log_header)
        week = self._get_task_week(task, log_header, log_data, log_idx)
        week_str = week if week else ""
        task.status = "??失敗"  # 標記任務為失敗
        
        before_hp = player.hp_current
        before_mp = player.mp_current
        # 計算 HP 扣除量
        if getattr(player, "shield_fail", False):
            # 若啟用了護盾狀態，則不受傷
            delta_hp = 0
            setattr(player, "shield_fail", False)
        else:
            delta_hp = task.fail_hp  # 基礎傷害
            passive_ctx = skills.SkillContext(
                actor=player,
                task=task,
                state=self,
                week_str=week_str,
                log_data=log_data,
                log_idx=log_idx,
                delta_hp=delta_hp,
            )
            passive_result = skills.apply_passive("on_fail", passive_ctx)
            delta_hp = passive_result.get("delta_hp", delta_hp)
        
        # 更新玩家 HP（確保不低於 0，不高於最大值）
        player.hp_current = validators.clamp(player.hp_current + delta_hp, 0, player.hp_max)
        penalty_triggered = before_hp > 0 and player.hp_current == 0
        if penalty_triggered:
            player.penalty_weeks = 2
            player.mp_current = 0
        
        # 保存變更並記錄日誌
        self._persist_task_and_player(
            task,
            player,
            delta_hp=delta_hp,
            delta_mp=0,
            delta_exp=0,
            desc="任務失敗",
            week=week_str,
            update_task=True,
        )
        if penalty_triggered:
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=week_str,
                player=player.name,
                type_="懲罰",
                code="HP_ZERO_PENALTY",
                name="死亡懲罰",
                desc="HP 歸零，MP 兩週歸零",
                target=player.name,
                delta_hp=-before_hp,
                delta_mp=-before_mp,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
            self.repo.append_log(log)
        # 任務保留到週結算再清除

    def use_skill(
        self,
        skill_id: str,
        actor: models.PlayerState,
        target: Optional[models.PlayerState],
        task: Optional[models.Task] = None,
        skill_state: Optional[models.SkillState] = None,
    ) -> bool:
        """使用技能：驗證、應用效果、持久化並記錄。
        
        Args:
            skill_id: 技能 ID（如 'GeA001'）
            actor: 使用技能的玩家
            target: 技能目標玩家（可選）
            task: 進行中的任務（可選）
            skill_state: 技能狀態物件，用於追蹤使用次數（可選）
            
        Returns:
            True 若技能成功應用，否則返回 False
            
        流程:
            1. 刷新狀態並記錄變更前的數據
            2. 應用 MP 折扣（如 MaP002 被動在首次使用魔法技能時）
            3. 呼叫 skills.apply_active() 執行技能邏輯
            4. 應用後續效果（如 SwP003 被動在使用 GeA002 時回血）
            5. 保存玩家和任務狀態
            6. 計算變更差值
            7. 記錄技能使用日誌和目標影響日誌
            8. 減少技能剩餘使用次數
        """
        self.refresh_state()
        log_header, log_data = self.repo.get_logs(limit=500)
        log_idx = self._log_indices(log_header)
        before_actor = (actor.hp_current, actor.mp_current, actor.exp)
        before_target = None
        if target:
            before_target = (target.hp_current, target.mp_current, target.exp)
        before_task = None
        if task:
            before_task = (task.difficulty, getattr(task, "extra_days", 0))

        week = self._get_task_week(task, log_header, log_data, log_idx) if task else None
        if not week:
            current_week = self.get_last_week_from_logs()
            week = str(current_week) if current_week > 0 else ""
        week_str = week if week else ""
        mp_discount = 0
        pre_ctx = skills.SkillContext(
            actor=actor,
            target=target,
            task=task,
            state=self,
            skill_state=skill_state,
            week_str=week_str,
            log_data=log_data,
            log_idx=log_idx,
        )
        if skill_state and (not skill_state.mp_cost or skill_state.mp_cost == 0):
            skill_def = self.repo.get_skill_definition(skill_id)
            if skill_def and skill_def.mp_cost:
                skill_state.mp_cost = skill_def.mp_cost
        passive_support = skills.apply_passive("on_support_used", pre_ctx)
        mp_discount = passive_support.get("mp_discount", 0)

        ctx = skills.SkillContext(
            actor=actor,
            target=target,
            task=task,
            state=self,
            skill_state=skill_state,
            mp_discount=mp_discount,
            skill_id=skill_id,
            week_str=week_str,
            log_data=log_data,
            log_idx=log_idx,
        )
        applied = skills.apply_active(skill_id, context=ctx)
        if not applied:
            return False
        if skill_id == "GeA002":
            skills.apply_passive("on_combo", ctx)

        if actor.penalty_weeks > 0:
            actor.mp_current = 0
        if target and target is not actor and getattr(target, "penalty_weeks", 0) > 0:
            target.mp_current = 0
        self.repo.save_player_state(actor)
        if target and target is not actor:
            self.repo.save_player_state(target)
        if task and before_task != (task.difficulty, getattr(task, "extra_days", 0)):
            self.repo.update_task_status(task)

        delta_hp = actor.hp_current - before_actor[0]
        delta_mp = actor.mp_current - before_actor[1]
        delta_exp = actor.exp - before_actor[2]
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=week_str,
            player=actor.name,
            type_="技能",
            code=skill_id,
            name=skill_state.name if skill_state else skill_id,
            desc="使用技能",
            target=target.name if target else "",
            delta_hp=delta_hp,
            delta_mp=delta_mp,
            delta_exp=delta_exp,
            hp=actor.hp_current,
            mp=actor.mp_current,
            exp=actor.exp,
        )
        self.repo.append_log(log)

        if skill_state and skill_state.remaining is not None:
            skill_state.remaining = max(0, skill_state.remaining - 1)
            self.repo.update_skill_state(skill_state)

        if target and before_target:
            target_delta_hp = target.hp_current - before_target[0]
            target_delta_mp = target.mp_current - before_target[1]
            target_delta_exp = target.exp - before_target[2]
            if any([target_delta_hp, target_delta_mp, target_delta_exp]):
                target_log = models.LogEntry(
                    date=time_utils.now().date().isoformat(),
                    week=week_str,
                    player=target.name,
                    type_="技能",
                    code=skill_id,
                    name=skill_id,
                    desc="技能影響",
                    target=actor.name,
                    delta_hp=target_delta_hp,
                    delta_mp=target_delta_mp,
                    delta_exp=target_delta_exp,
                    hp=target.hp_current,
                    mp=target.mp_current,
                    exp=target.exp,
                )
                self.repo.append_log(target_log)
        if (
            skill_id in {"GeA001", "PrA001"}
            and target
            and "PrP001" in self._get_player_passives(actor.name)
        ):
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=week_str,
                player=actor.name,
                type_="事件",
                code="PrP001",
                name="溫和引導",
                desc="支援標記",
                target=target.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=actor.hp_current,
                mp=actor.mp_current,
                exp=actor.exp,
            )
            self.repo.append_log(log)

        return True

    def mark_overdue_tasks(self) -> None:
        """檢查並標記所有逾期的任務為失敗。
        
        逾期判定：截止日期 + extra_days + time_bonus < 今天
        
        流程:
            1. 遍歷所有進行中的任務
            2. 解析截止日期（支援 Excel 序號或 ISO 格式字串）
            3. 計算實際截止時間（截止日 + 額外日數 + 時間獎勵）
            4. 若已逾期，自動失敗任務（扣血）
        """
        today = time_utils.now().date()
        status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}  # 已完成或已失敗的狀態
        for t in self.tasks:
            if t.status in status_done:
                continue  # 跳過已完成的任務
            deadline_date = self._parse_deadline(t.deadline)
            extra_days = getattr(t, "extra_days", 0)
            time_bonus = getattr(t, "time_bonus", 0)
            # 檢查是否逾期
            if deadline_date and deadline_date + datetime.timedelta(days=extra_days + time_bonus) < today:
                player = self._find_player(t.player)
                if player:
                    self.fail_task(t, player)

    def is_task_overdue(self, task: models.Task) -> bool:
        deadline_date = self._parse_deadline(task.deadline)
        if not deadline_date:
            return False
        extra_days = getattr(task, "extra_days", 0)
        time_bonus = getattr(task, "time_bonus", 0)
        return deadline_date + datetime.timedelta(days=extra_days + time_bonus) < time_utils.now().date()

    def count_incomplete_tasks_for_week(self, week: int) -> int:
        if week <= 0:
            return 0
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}
        count = 0
        for task in self.tasks:
            if task.status in status_done:
                continue
            task_week = self._get_task_week(task, header, data, idx)
            if task_week == str(week):
                count += 1
        return count

    def fail_incomplete_tasks_for_week(self, week: int) -> int:
        if week <= 0:
            return 0
        self.refresh_state()
        header, data = self.repo.get_logs(limit=500)
        idx = self._log_indices(header)
        status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}
        to_fail = []
        for task in self.tasks:
            if task.status in status_done:
                continue
            task_week = self._get_task_week(task, header, data, idx)
            if task_week == str(week):
                player = self._find_player(task.player)
                if player:
                    to_fail.append((task, player))
        for task, player in to_fail:
            self.fail_task(task, player)
        return len(to_fail)

    def _persist_task_and_player(
        self,
        task: models.Task,
        player: models.PlayerState,
        delta_hp: int,
        delta_mp: int,
        delta_exp: int,
        desc: Optional[str] = None,
        update_task: bool = True,
        week: str = "",
    ) -> None:
        """內部方法：保存任務和玩家狀態變更，並記錄日誌。
        
        Args:
            task: 任務物件
            player: 玩家物件
            delta_hp: HP 變化量
            delta_mp: MP 變化量
            delta_exp: EXP 變化量
            desc: 日誌描述（如未提供則根據任務狀態自動生成）
            update_task: 是否更新任務狀態到資料庫
            week: 週數
        """
        if update_task:
            self.repo.update_task_status(task)
        if getattr(player, "penalty_weeks", 0) > 0:
            player.mp_current = 0
        self.repo.save_player_state(player)
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=week,
            player=player.name,
            type_="任務",
            code=task.monster_id,
            name=task.name,
            desc=desc if desc is not None else ("完成" if task.status == "?擊殺" else "失敗"),
            target=player.name,
            delta_hp=delta_hp,
            delta_mp=delta_mp,
            delta_exp=delta_exp,
            hp=player.hp_current,
            mp=player.mp_current,
            exp=player.exp,
        )
        self.repo.append_log(log)

    def _check_level_up(self, player: models.PlayerState) -> Optional[models.LogEntry]:
        """檢查玩家是否升級，若升級則更新上限並回滿 HP/MP，返回升級日誌。
        
        Args:
            player: 玩家物件
            
        Returns:
            升級日誌，若無升級則返回 None
            
        流程:
            1. 從等級表查詢累積 EXP 對應的目標等級
            2. 若目標等級 > 當前等級，則升級
            3. 根據新等級從等級表查詢 HP/MP 增量
            4. 更新玩家的等級、HP/MP 上限，並回滿 HP/MP
            5. 返回升級日誌以供記錄
        """
        levels, hp_inc, mp_inc, exp_req = self.repo.get_level_table()
        if not levels:
            return None
        old_level = player.level
        old_hp = player.hp_current
        old_mp = player.mp_current
        target_level = player.level
        # 根據 EXP 查詢目標等級
        for lvl, need_exp in zip(levels, exp_req):
            if player.exp >= need_exp:
                target_level = max(target_level, lvl)
        # 執行升級
        if target_level > player.level:
            old = player.level
            player.level = target_level
            idx = levels.index(target_level)
            # 更新 HP/MP 上限
            player.hp_max = hp_inc[idx] if idx < len(hp_inc) else player.hp_max
            player.mp_max = mp_inc[idx] if idx < len(mp_inc) else player.mp_max
            # 回滿 HP/MP
            player.hp_current = player.hp_max
            player.mp_current = player.mp_max
            self._grant_random_job_skills(player, target_level - old)
            return models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week="",
                player=player.name,
                type_="升級",
                code="LEVEL_UP",
                name="升級",
                desc=f"Lv{old_level}->{player.level}",
                target=player.name,
                delta_hp=player.hp_current - old_hp,
                delta_mp=player.mp_current - old_mp,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
        return None

    def _grant_random_job_skills(self, player: models.PlayerState, count: int) -> None:
        if count <= 0:
            return
        header, data, skill_states = self.repo.get_skill_states_with_header()
        if not header:
            return
        owned = {
            s.skill_id
            for s in skill_states
            if s.player == player.name and s.enabled and s.enabled.upper() == "Y"
        }
        candidates = [
            s
            for s in skill_states
            if s.player == player.name
            and s.job == player.job
            and s.skill_id not in owned
        ]
        for _ in range(count):
            if not candidates:
                break
            choice = random.choice(candidates)
            choice.enabled = "Y"
            choice.remaining = choice.total_uses
            self.repo.update_skill_state(choice)
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week="",
                player=player.name,
                type_="技能",
                code=choice.skill_id,
                name=choice.name,
                desc="升級獲得技能",
                target=player.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
            self.repo.append_log(log)
            owned.add(choice.skill_id)
            candidates = [c for c in candidates if c.skill_id not in owned]

    def resolve_boss_week(
        self,
        boss: models.BossInfo,
        week: int,
        hours_by_player: dict,
        tasks_done_by_player: dict,
        last_hit_player: Optional[str] = None,
    ) -> tuple[bool, str, dict]:
        """BOSS 週結算：驗證條件並發放獎勵。
        
        Args:
            boss: BOSS 資訊（包含獎勵設定）
            week: 結算週數
            hours_by_player: 各玩家的運動時數字典 {玩家名: 時數}
            tasks_done_by_player: 各玩家是否完成指定任務的字典 {玩家名: 布林值}
            last_hit_player: 擊殺 BOSS 的最後一人（獲得額外獎勵）
            
        Returns:
            (成功布林值, 訊息)
            
        流程:
            1. 檢查該週 BOSS 是否已結算（避免重複）
            2. 驗證總運動時數是否達到 BOSS 要求
            3. 驗證所有玩家是否完成指定任務
            4. 為每個玩家計算獎勵
               - 基礎獎勵 + 時數額外獎勵（時數 × 時數獎勵係數）
               - 若為最後一人，加上最後擊殺獎勵
            5. 檢查升級並記錄日誌
            6. 更新首頁狀態（前進到下一個地圖）
        """
        self.refresh_state()
        log_header, log_data = self.repo.get_logs(limit=500)
        log_idx = self._log_indices(log_header)
        week_str = str(week)
        # 檢查該週 BOSS 是否已結算
        if self._has_boss_settlement(week_str, boss.boss_id, log_data, log_idx):
            return False, "本週 BOSS 已結算。", {}

        # 驗證運動時數
        total_hours = 0.0
        for value in hours_by_player.values():
            try:
                total_hours += float(value)
            except Exception:
                continue
        if boss.required_hours and total_hours < boss.required_hours:
            return False, "累計運動時數不足，未達成 BOSS 條件。", {}
        
        # 驗證玩家任務完成情況
        for p in self.players:
            if not tasks_done_by_player.get(p.name):
                return False, "仍有玩家未完成 BOSS 指定任務。", {}

        results = {}
        # 為每個玩家發放獎勵
        for p in self.players:
            hours = 0.0
            try:
                hours = float(hours_by_player.get(p.name, 0))
            except Exception:
                hours = 0.0
            # 計算獎勵
            extra_exp = int(hours * boss.extra_exp_per_hour) if boss.extra_exp_per_hour else 0
            exp_gain = boss.clear_reward + extra_exp
            # 若該玩家是最後一人，額外獎勵
            if last_hit_player and p.name == last_hit_player:
                exp_gain += boss.last_hit_reward
            # 更新玩家 EXP 並檢查升級
            p.exp += exp_gain
            results[p.name] = exp_gain
            level_log = self._check_level_up(p)
            self.repo.save_player_state(p)
            # 記錄 BOSS 結算日誌
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=week_str,
                player=p.name,
                type_="BOSS",
                code=boss.boss_id,
                name=boss.name,
                desc="BOSS 結算",
                target=p.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=exp_gain,
                hp=p.hp_current,
                mp=p.mp_current,
                exp=p.exp,
            )
            self.repo.append_log(log)
            if level_log:
                self.repo.append_log(level_log)

        return True, "BOSS 結算完成。", {"exp_by_player": results}

    def record_boss_contributions(
        self,
        boss: models.BossInfo,
        week: int,
        hours_by_player: dict,
        tasks_done_by_player: dict,
        active_player: Optional[str] = None,
    ) -> tuple[bool, str]:
        if not boss or week <= 0:
            return False, "缺少 BOSS 或週數。"
        self.refresh_state()
        for player in self.players:
            if active_player and player.name != active_player:
                continue
            hours = hours_by_player.get(player.name, 0)
            done = bool(tasks_done_by_player.get(player.name))
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=str(week),
                player=player.name,
                type_="BOSS貢獻",
                code=boss.boss_id,
                name=boss.name,
                desc=f"hours={hours};task={1 if done else 0}",
                target=player.name,
                delta_hp=0,
                delta_mp=0,
                delta_exp=0,
                hp=player.hp_current,
                mp=player.mp_current,
                exp=player.exp,
            )
            self.repo.append_log(log)
        return True, "已更新 BOSS 貢獻。"

    def get_boss_contributions(self, boss_id: str, week: int) -> dict:
        results: dict[str, dict] = {}
        if not boss_id or week <= 0:
            return results
        header, data = self.repo.get_logs(limit=500)
        if not header:
            return results
        idx = self._log_indices(header)
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        idx_player = idx.get("player")
        idx_desc = idx.get("desc")
        if idx_week is None or idx_type is None or idx_code is None or idx_player is None or idx_desc is None:
            return results
        week_str = str(week)
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code, idx_player, idx_desc):
                continue
            if str(row[idx_week]).strip() != week_str:
                continue
            if row[idx_type] != "BOSS貢獻":
                continue
            if row[idx_code] != boss_id:
                continue
            player = str(row[idx_player]).strip()
            if not player:
                continue
            desc = str(row[idx_desc])
            hours = 0.0
            done = False
            for part in desc.split(";"):
                if part.startswith("hours="):
                    try:
                        hours = float(part.split("=", 1)[1])
                    except Exception:
                        hours = 0.0
                if part.startswith("task="):
                    done = part.split("=", 1)[1].strip() == "1"
            results[player] = {"hours": hours, "task_done": done}
        return results

    def _find_player(self, name: str) -> Optional[models.PlayerState]:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def _log_indices(self, header: List[str]) -> dict:
        def idx_any(names: List[str]) -> Optional[int]:
            for name in names:
                if name in header:
                    return header.index(name)
            for idx, head in enumerate(header):
                for name in names:
                    if name and name in head:
                        return idx
            return None

        return {
            "date": idx_any(["日期", "Date"]),
            "week": idx_any(["週數"]),
            "player": idx_any(["玩家"]),
            "type": idx_any(["類型"]),
            "code": idx_any(["代碼"]),
            "desc": idx_any(["效果說明", "說明", "敘述", "描述"]),
            "target": idx_any(["對象", "目標"]),
        }

    def _get_task_week(
        self,
        task: Optional[models.Task],
        header: List[str],
        data: List[List[str]],
        idx: dict,
    ) -> Optional[str]:
        if not task or not header:
            return None
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_code is None:
            return None
        for row in reversed(data):
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if row[idx_type] != "抽怪物":
                continue
            if row[idx_code] != task.monster_id:
                continue
            value = str(row[idx_week]).strip()
            return value if value else None
        return None

    def _get_event_codes_for_week(self, week: Optional[str]) -> List[str]:
        if not week:
            return []
        try:
            week_int = int(float(week))
        except Exception:
            return []
        event = self.get_event_for_week(week_int)
        if not event or not event.effect_code:
            return []
        return self.parse_event_codes(event.effect_code)

    def _get_player_passives(self, player_name: str) -> set:
        passives = set()
        for state in self.skill_states:
            if state.player != player_name:
                continue
            kind = (state.kind or "").strip()
            if not kind:
                continue
            if "P" in kind or "被動" in kind:
                if state.enabled and state.enabled.upper() == "Y":
                    passives.add(state.skill_id)
        return passives

    def _has_team_completion(self, week: str, data: List[List[str]], idx: dict) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_desc = idx.get("desc")
        if idx_week is None or idx_type is None or idx_desc is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_desc):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "任務":
                continue
            desc = str(row[idx_desc])
            if "擊敗" in desc or "完成" in desc:
                return True
        return False

    def _has_player_completion(
        self, player: str, week: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_desc = idx.get("desc")
        idx_player = idx.get("player")
        if idx_week is None or idx_type is None or idx_desc is None or idx_player is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_desc, idx_player):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "任務":
                continue
            if row[idx_player] != player:
                continue
            desc = str(row[idx_desc])
            if "擊敗" in desc or "完成" in desc:
                return True
        return False

    def _count_player_completions(
        self, player: str, week: str, data: List[List[str]], idx: dict
    ) -> int:
        if not week:
            return 0
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_desc = idx.get("desc")
        idx_player = idx.get("player")
        if idx_week is None or idx_type is None or idx_desc is None or idx_player is None:
            return 0
        count = 0
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_desc, idx_player):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "任務":
                continue
            if row[idx_player] != player:
                continue
            desc = str(row[idx_desc])
            if "擊敗" in desc or "完成" in desc:
                count += 1
        return count

    def _has_player_failure(
        self, player: str, week: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_desc = idx.get("desc")
        idx_player = idx.get("player")
        if idx_week is None or idx_type is None or idx_desc is None or idx_player is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_desc, idx_player):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "任務":
                continue
            if row[idx_player] != player:
                continue
            desc = str(row[idx_desc])
            if "失敗" in desc:
                return True
        return False

    def _has_boss_settlement(
        self, week: str, boss_id: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "BOSS":
                continue
            if row[idx_code] == boss_id:
                return True
        return False

    def _has_skill_usage(
        self, player: str, week: str, codes: set, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_player = idx.get("player")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_player is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_player, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "技能":
                continue
            if row[idx_player] != player:
                continue
            if row[idx_code] in codes:
                return True
        return False

    def _has_event_code(self, week: str, code: str, data: List[List[str]], idx: dict) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "事件":
                continue
            if row[idx_code] == code:
                return True
        return False

    def _has_event_code_for_player(
        self, week: str, code: str, player: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        idx_player = idx.get("player")
        if idx_week is None or idx_type is None or idx_code is None or idx_player is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code, idx_player):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "事件":
                continue
            if row[idx_code] != code:
                continue
            if row[idx_player] == player:
                return True
        return False

    def _has_event_choice(self, week: str, data: List[List[str]], idx: dict) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "事件":
                continue
            if row[idx_code] == "CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5":
                return True
        return False

    def _adjust_difficulty(self, diff: str, delta: int) -> str:
        order = ["易", "中", "難"]
        for idx, label in enumerate(order):
            if label in diff:
                new_idx = max(0, min(len(order) - 1, idx + delta))
                return order[new_idx]
        return diff

    def _team_combo_used(self, week: str, data: List[List[str]], idx: dict) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_type is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "技能":
                continue
            if row[idx_code] == "GeA002":
                return True
        return False

    def _has_event_bonus_log(
        self, player: str, week: str, code: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_player = idx.get("player")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_player is None or idx_type is None or idx_code is None:
            return False
        for row in data:
            if len(row) <= max(idx_week, idx_player, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_player] != player:
                continue
            if row[idx_type] != "事件":
                continue
            if row[idx_code] == code:
                return True
        return False

    def _has_support_bonus(
        self, player: str, week: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        idx_target = idx.get("target")
        idx_player = idx.get("player")
        idx_desc = idx.get("desc")
        if (
            idx_week is None
            or idx_type is None
            or idx_code is None
            or idx_target is None
            or idx_player is None
        ):
            return False
        last_completion = -1
        support_index = -1
        bonus_index = -1
        for i, row in enumerate(data):
            if len(row) <= max(idx_week, idx_type, idx_code, idx_target, idx_player):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] == "任務" and row[idx_player] == player:
                if idx_desc is None or len(row) <= idx_desc:
                    continue
                desc = str(row[idx_desc])
                if "擊敗" in desc or "完成" in desc:
                    last_completion = i
            if row[idx_type] == "事件" and row[idx_code] == "PrP001":
                if row[idx_target] == player:
                    support_index = max(support_index, i)
            if row[idx_type] == "事件" and row[idx_code] == "PrP001_BONUS":
                if row[idx_player] == player:
                    bonus_index = max(bonus_index, i)
        if support_index <= last_completion:
            return False
        if bonus_index > support_index:
            return False
        return True

    def _append_event_bonus_log(
        self, player_state: models.PlayerState, week: str, code: str, delta_exp: int
    ) -> None:
        log = models.LogEntry(
            date=time_utils.now().date().isoformat(),
            week=week,
            player=player_state.name,
            type_="事件",
            code=code,
            name=code,
            desc="事件加成",
            target=player_state.name,
            delta_hp=0,
            delta_mp=0,
            delta_exp=delta_exp,
            hp=player_state.hp_current,
            mp=player_state.mp_current,
            exp=player_state.exp,
        )
        self.repo.append_log(log)

    def _has_recent_skill_after_last_completion(
        self, player: str, week: str, codes: set, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_player = idx.get("player")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        if idx_week is None or idx_player is None or idx_type is None or idx_code is None:
            return False
        last_skill = -1
        last_completion = -1
        for i, row in enumerate(data):
            if len(row) <= max(idx_week, idx_player, idx_type, idx_code):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_player] != player:
                continue
            if row[idx_type] == "技能" and row[idx_code] in codes:
                last_skill = i
            if row[idx_type] == "任務":
                last_completion = i
        return last_skill > last_completion

    def _has_recent_support_after_last_completion(
        self, player: str, week: str, codes: set, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_player = idx.get("player")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        idx_desc = idx.get("desc")
        if (
            idx_week is None
            or idx_player is None
            or idx_type is None
            or idx_code is None
            or idx_desc is None
        ):
            return False
        last_support = -1
        last_completion = -1
        for i, row in enumerate(data):
            if len(row) <= max(idx_week, idx_player, idx_type, idx_code, idx_desc):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_player] != player:
                continue
            if row[idx_type] == "技能" and row[idx_code] in codes and "影響" in str(row[idx_desc]):
                last_support = i
            if row[idx_type] == "任務":
                last_completion = i
        return last_support > last_completion

    def _last_completion_was_yesterday(
        self, player: str, today: datetime.date, week: str, data: List[List[str]], idx: dict
    ) -> bool:
        if not week:
            return False
        idx_week = idx.get("week")
        idx_type = idx.get("type")
        idx_desc = idx.get("desc")
        idx_player = idx.get("player")
        idx_date = idx.get("date")
        if (
            idx_week is None
            or idx_type is None
            or idx_desc is None
            or idx_player is None
            or idx_date is None
        ):
            return False
        last_date = None
        for row in data:
            if len(row) <= max(idx_week, idx_type, idx_desc, idx_player, idx_date):
                continue
            if str(row[idx_week]).strip() != week:
                continue
            if row[idx_type] != "任務":
                continue
            if row[idx_player] != player:
                continue
            desc = str(row[idx_desc])
            if "擊敗" not in desc and "完成" not in desc:
                continue
            date_text = str(row[idx_date]).strip()
            try:
                last_date = datetime.date.fromisoformat(date_text)
            except Exception:
                continue
        if not last_date:
            return False
        return last_date == today - datetime.timedelta(days=1)

    def _apply_empathy_feedback_for_completion(
        self,
        completed_player: models.PlayerState,
        week: str,
        data: List[List[str]],
        idx: dict,
        delta_mp: int = 1,
        weekly_cap: int = 2,
    ) -> None:
        if not week:
            return
        idx_week = idx.get("week")
        idx_player = idx.get("player")
        idx_type = idx.get("type")
        idx_code = idx.get("code")
        idx_target = idx.get("target")
        if (
            idx_week is None
            or idx_player is None
            or idx_type is None
            or idx_code is None
            or idx_target is None
        ):
            return
        for rescuer in self.players:
            passives = self._get_player_passives(rescuer.name)
            if "PrP002" not in passives:
                continue
            bonus_count = 0
            rescued_target = False
            for row in data:
                if len(row) <= max(idx_week, idx_player, idx_type, idx_code, idx_target):
                    continue
                if str(row[idx_week]).strip() != week:
                    continue
                if row[idx_player] != rescuer.name:
                    continue
                if row[idx_type] == "事件" and row[idx_code] == "PrP002":
                    bonus_count += 1
                if (
                    row[idx_type] == "技能"
                    and row[idx_code] in {"GeA001", "PrA001", "ArA001"}
                    and row[idx_target] == completed_player.name
                ):
                    rescued_target = True
            if not rescued_target or bonus_count >= weekly_cap:
                continue
            rescuer.mp_current = validators.clamp(
                rescuer.mp_current + delta_mp, 0, rescuer.mp_max
            )
            if rescuer.penalty_weeks > 0:
                rescuer.mp_current = 0
            self.repo.save_player_state(rescuer)
            log = models.LogEntry(
                date=time_utils.now().date().isoformat(),
                week=week,
                player=rescuer.name,
                type_="事件",
                code="PrP002",
                name="共感回饋",
                desc="救援回饋",
                target=completed_player.name,
                delta_hp=0,
                delta_mp=delta_mp,
                delta_exp=0,
                hp=rescuer.hp_current,
                mp=rescuer.mp_current,
                exp=rescuer.exp,
            )
            self.repo.append_log(log)

    def _parse_deadline(self, deadline: Optional[str]) -> Optional[datetime.date]:
        if not deadline:
            return None
        try:
            if deadline.isdigit():
                return time_utils.excel_serial_to_date(float(deadline))
        except Exception:
            pass
        try:
            return datetime.date.fromisoformat(deadline)
        except Exception:
            return None
