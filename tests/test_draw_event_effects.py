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

from domain.logic import Logic
from domain import models


class FakeRepo:
    def __init__(self, events=None, logs=None, monsters=None, players=None):
        self._events = events or []
        self._logs_header = ["日期", "週數", "玩家", "類型", "代碼", "名稱", "效果說明", "對象"]
        self._logs = logs or []
        self._monsters = monsters or []
        self._players = players or []
        self.added_tasks = []
        self.appended_logs = []

    def get_events(self):
        return self._events

    def get_logs(self, limit=None):
        data = self._logs[-limit:] if limit else self._logs
        return self._logs_header, data

    def get_monsters(self):
        return self._monsters

    def get_player_states(self):
        return list(self._players)

    def get_tasks(self):
        return list(self.added_tasks)

    def get_skill_states(self):
        return []

    def add_task(self, task):
        self.added_tasks.append(task)

    def append_log(self, log):
        self.appended_logs.append(log)
        self._logs.append(log.to_row() if hasattr(log, "to_row") else log)

    def update_task_status(self, task):
        return True


class DrawEventEffectsTests(unittest.TestCase):
    def test_all_monster_lv_plus_one_bumps_pool(self):
        event = models.Event(
            event_id="E1",
            category="B",
            name="Boost",
            effect_code="ALL_MONSTER_LV+1",
            description="",
            note="",
        )
        logs = [["2026-01-10", "1", "全員", "抽事件", "E1", "Boost", "", "全隊"]]
        monsters = [
            models.Monster(
                monster_id="M1",
                category="",
                name="Easy",
                description="",
                difficulty="易",
                content="",
                time_limit_days=2,
                success_exp=1,
                fail_hp=1,
            ),
            models.Monster(
                monster_id="M2",
                category="",
                name="Medium",
                description="",
                difficulty="中",
                content="",
                time_limit_days=2,
                success_exp=3,
                fail_hp=2,
            ),
        ]
        players = [
            models.PlayerState(
                name="P1",
                job="Job",
                level=1,
                exp=0,
                hp_current=10,
                mp_current=5,
                hp_max=10,
                mp_max=5,
            )
        ]
        repo = FakeRepo(events=[event], logs=logs, monsters=monsters, players=players)
        logic = Logic(repo)
        map_info = models.MapInfo(
            map_id="MAP1",
            name="Map",
            week=1,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B1",
        )
        tasks = logic.draw_monsters_for_map(map_info, week=1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].difficulty, "中")

    def test_monster_time_minus_one_day(self):
        event = models.Event(
            event_id="E2",
            category="D",
            name="Shorten",
            effect_code="MONSTER_TIME-1_DAY",
            description="",
            note="",
        )
        logs = [["2026-01-10", "1", "全員", "抽事件", "E2", "Shorten", "", "全隊"]]
        monsters = [
            models.Monster(
                monster_id="M1",
                category="",
                name="Easy",
                description="",
                difficulty="易",
                content="",
                time_limit_days=3,
                success_exp=1,
                fail_hp=1,
            )
        ]
        players = [
            models.PlayerState(
                name="P1",
                job="Job",
                level=1,
                exp=0,
                hp_current=10,
                mp_current=5,
                hp_max=10,
                mp_max=5,
            )
        ]
        repo = FakeRepo(events=[event], logs=logs, monsters=monsters, players=players)
        logic = Logic(repo)
        map_info = models.MapInfo(
            map_id="MAP1",
            name="Map",
            week=1,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B1",
        )
        tasks = logic.draw_monsters_for_map(map_info, week=1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].time_limit_days, 2)

    def test_choice_event_applies_bonus_exp(self):
        event = models.Event(
            event_id="E3",
            category="B",
            name="Choice",
            effect_code="CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5",
            description="",
            note="",
        )
        logs = [["2026-01-10", "1", "全員", "抽事件", "E3", "Choice", "", "全隊"]]
        monsters = [
            models.Monster(
                monster_id="M1",
                category="",
                name="Easy",
                description="",
                difficulty="易",
                content="",
                time_limit_days=2,
                success_exp=1,
                fail_hp=1,
            )
        ]
        players = [
            models.PlayerState(
                name="P1",
                job="Job",
                level=1,
                exp=0,
                hp_current=10,
                mp_current=5,
                hp_max=10,
                mp_max=5,
            )
        ]
        repo = FakeRepo(events=[event], logs=logs, monsters=monsters, players=players)
        logic = Logic(repo)
        map_info = models.MapInfo(
            map_id="MAP1",
            name="Map",
            week=1,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B1",
        )
        tasks = logic.draw_monsters_for_map(map_info, week=1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].success_exp, 1)
        success, _ = logic.apply_choice_monster_event(1, "B")
        self.assertTrue(success)
        self.assertEqual(tasks[0].success_exp, 6)


if __name__ == "__main__":
    unittest.main()
