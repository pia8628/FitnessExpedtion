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
    def __init__(self, logs=None, maps=None, players=None, home_week=1, home_map_id=None):
        self._logs_header = ["日期", "週數", "玩家", "類型", "代碼", "名稱", "效果說明", "對象"]
        self._logs = logs or []
        self._maps = maps or []
        self._players = players or []
        self._home_week = home_week
        self._home_map_id = home_map_id
        self.updated_home = None
        self.saved_players = []
        self.appended_logs = []
        self.job_base_stats = {}
        self.level_table = ([], [], [], [])

    def get_logs(self, limit=None):
        data = self._logs[-limit:] if limit else self._logs
        return self._logs_header, data

    def get_maps(self):
        return self._maps

    def get_home_status(self):
        return self._home_week, self._home_map_id

    def update_home_status(self, week, map_id):
        self.updated_home = (week, map_id)
        self._home_week = week
        self._home_map_id = map_id

    def get_player_states(self):
        return list(self._players)

    def get_tasks(self):
        return []

    def get_skill_states(self):
        return []

    def get_level_table(self):
        return self.level_table

    def get_job_base_stats(self, job_code):
        return self.job_base_stats.get(job_code, (0, 0))

    def save_player_state(self, state):
        self.saved_players.append(state)
        return True

    def update_task_status(self, task):
        return True

    def append_log(self, log):
        self.appended_logs.append(log)


class LogicMapProgressTests(unittest.TestCase):
    def test_map_progress_counts_logs(self):
        logs = [
            ["2026-01-10", "1", "全員", "地圖", "M1", "Map1", "", "M1"],
            ["2026-01-11", "2", "全員", "地圖", "M1", "Map1", "", "M1"],
            ["2026-01-12", "3", "全員", "地圖", "M2", "Map2", "", "M2"],
        ]
        repo = FakeRepo(logs=logs)
        logic = Logic(repo)
        self.assertEqual(logic.get_map_progress("M1"), 2)
        self.assertEqual(logic.get_map_progress("M2"), 1)

    def test_is_boss_stage(self):
        logs = [
            ["2026-01-10", "1", "全員", "地圖", "M1", "Map1", "", "M1"],
        ]
        map_info = models.MapInfo(
            map_id="M1",
            name="Map1",
            week=2,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B1",
        )
        repo = FakeRepo(logs=logs)
        logic = Logic(repo)
        self.assertFalse(logic.is_boss_stage(map_info))

        logs.append(["2026-01-11", "2", "全員", "地圖", "M1", "Map1", "", "M1"])
        repo = FakeRepo(logs=logs)
        logic = Logic(repo)
        self.assertTrue(logic.is_boss_stage(map_info))

    def test_resolve_boss_week_advances_map(self):
        map1 = models.MapInfo(
            map_id="M1",
            name="Map1",
            week=2,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B1",
        )
        map2 = models.MapInfo(
            map_id="M2",
            name="Map2",
            week=2,
            difficulty_count=1,
            easy_rate=1.0,
            medium_rate=0.0,
            hard_rate=0.0,
            boss_id="B2",
        )
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
            ),
            models.PlayerState(
                name="P2",
                job="Job",
                level=1,
                exp=0,
                hp_current=10,
                mp_current=5,
                hp_max=10,
                mp_max=5,
            ),
        ]
        boss = models.BossInfo(
            boss_id="B1",
            name="Boss",
            required_hours=0.0,
            required_tasks="",
            clear_reward=1,
            extra_exp_per_hour=0.0,
            last_hit_reward=0,
        )
        repo = FakeRepo(maps=[map1, map2], players=players, home_week=3, home_map_id="M1")
        logic = Logic(repo)
        success, _, _ = logic.resolve_boss_week(
            boss,
            week=3,
            hours_by_player={"P1": 0, "P2": 0},
            tasks_done_by_player={"P1": True, "P2": True},
            last_hit_player=None,
        )
        self.assertTrue(success)
        self.assertEqual(repo.updated_home, (3, "M2"))

    def test_check_level_up_uses_job_base_plus_level_bonus(self):
        repo = FakeRepo()
        repo.level_table = (
            [1, 2, 3],
            [2, 5, 9],   # HP 增量
            [1, 3, 4],   # MP 增量
            [0, 10, 30], # 升級需求 EXP
        )
        repo.job_base_stats = {"Warrior": (20, 8)}
        logic = Logic(repo)
        logic._grant_random_job_skills = lambda *_args, **_kwargs: None
        player = models.PlayerState(
            name="P1",
            job="Warrior",
            level=1,
            exp=10,
            hp_current=7,
            mp_current=2,
            hp_max=22,
            mp_max=9,
        )

        log = logic._check_level_up(player)

        self.assertIsNotNone(log)
        self.assertEqual(player.level, 2)
        self.assertEqual(player.hp_max, 25)  # 20 + 5
        self.assertEqual(player.mp_max, 11)  # 8 + 3
        self.assertEqual(player.hp_current, 25)
        self.assertEqual(player.mp_current, 11)

    def test_fail_task_triggers_penalty_and_revives_hp(self):
        player = models.PlayerState(
            name="P1",
            job="Warrior",
            level=1,
            exp=0,
            hp_current=3,
            mp_current=5,
            hp_max=10,
            mp_max=8,
        )
        task = models.Task(
            monster_id="M1",
            player="P1",
            name="Task",
            difficulty="E",
            content="",
            start_date="2026-02-01",
            deadline="2026-02-02",
            status="進行中",
            success_exp=0,
            fail_hp=-10,
        )
        repo = FakeRepo(players=[player])
        logic = Logic(repo)

        logic.fail_task(task, player)

        self.assertEqual(player.penalty_weeks, 2)
        self.assertEqual(player.mp_current, 0)
        self.assertEqual(player.hp_current, 5)  # 10 // 2


if __name__ == "__main__":
    unittest.main()
