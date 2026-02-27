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
    def __init__(self):
        self.players = []
        self.tasks = []
        self.skill_states = []
        self.events = []
        self.monsters = []
        self.logs_header = ["日期", "週數", "玩家", "類型", "代碼", "名稱", "效果說明", "對象"]
        self.logs = []
        self.saved_players = []
        self.updated_tasks = []
        self.updated_skill_states = []
        self.home_status = (3, "M1")
        self.home_updates = []
        self.level_table = ([], [], [], [])
        self.added_skill_states = []
        self.force_skill_update_fail = False

    def get_player_states(self):
        return list(self.players)

    def get_tasks(self):
        return list(self.tasks)

    def get_skill_states(self):
        return list(self.skill_states)

    def get_logs(self, limit=None):
        data = self.logs[-limit:] if limit else self.logs
        return self.logs_header, data

    def get_events(self):
        return list(self.events)

    def get_level_table(self):
        return self.level_table

    def get_job_base_stats(self, _job_code):
        return (20, 10)

    def update_task_status(self, task):
        self.updated_tasks.append(task)
        return True

    def save_player_state(self, state):
        self.saved_players.append(state)
        return True

    def append_log(self, log):
        self.logs.append(log.to_row() if hasattr(log, "to_row") else log)

    def get_skill_states_with_header(self):
        return ["玩家", "技能ID"], [], list(self.skill_states)

    def update_skill_state(self, state):
        self.updated_skill_states.append(state)
        if self.force_skill_update_fail:
            return False
        return True

    def add_skill_state(self, state):
        self.added_skill_states.append(state)
        self.skill_states.append(state)
        return True

    def get_monsters(self):
        return list(self.monsters)

    def add_task(self, task):
        self.tasks.append(task)

    def get_home_status(self):
        return self.home_status

    def update_home_status(self, week, map_id):
        self.home_updates.append((week, map_id))
        self.home_status = (week, map_id)

    def get_job_skill_pool(self, _job_code):
        return []

    def get_skill_definition(self, _skill_id):
        return None


class KillModesAndLevelupTests(unittest.TestCase):
    def _make_task(self, exp=10):
        return models.Task(
            monster_id="M1",
            player="P1",
            name="Task",
            difficulty="E",
            content="Run 30 min",
            start_date="2026-02-27",
            deadline="2026-02-28",
            status="進行中",
            success_exp=exp,
            fail_hp=-1,
        )

    def _make_player(self):
        return models.PlayerState(
            name="P1",
            job="Archer",
            level=1,
            exp=0,
            hp_current=10,
            mp_current=5,
            hp_max=10,
            mp_max=5,
        )

    def test_complete_task_outcome_exp_rules(self):
        repo = FakeRepo()
        player = self._make_player()
        task = self._make_task(exp=11)
        repo.players = [player]
        repo.tasks = [task]
        logic = Logic(repo)

        logic.complete_task(task, player, outcome="perfect")
        self.assertEqual(player.exp, 11)

        player2 = self._make_player()
        task2 = self._make_task(exp=11)
        repo.players = [player2]
        repo.tasks = [task2]
        logic = Logic(repo)
        logic.complete_task(task2, player2, outcome="normal")
        self.assertEqual(player2.exp, 7)

    def test_levelup_skill_pool_job_plus_general_and_dedup(self):
        repo = FakeRepo()
        player = self._make_player()
        repo.skill_states = [
            models.SkillState("P1", "Archer", "ArA001", "JobSkill", "主動", 1, "N", None, None, "", ""),
            models.SkillState("P1", "Archer", "GeA010", "GeneralSkill", "主動", 1, "N", None, None, "", ""),
            models.SkillState("P1", "Archer", "MaA001", "OtherJob", "主動", 1, "N", None, None, "", ""),
            models.SkillState("P1", "Archer", "ArA002", "Owned", "主動", 1, "Y", None, None, "", ""),
        ]
        logic = Logic(repo)
        granted = logic._grant_random_job_skills(player, 10)

        granted_ids = {s.skill_id for s in granted}
        self.assertIn("ArA001", granted_ids)
        self.assertIn("GeA010", granted_ids)
        self.assertNotIn("MaA001", granted_ids)
        self.assertNotIn("ArA002", granted_ids)

    def test_levelup_empty_candidates_pushes_no_skill_notification(self):
        repo = FakeRepo()
        player = self._make_player()
        player.exp = 100
        repo.level_table = ([1, 2], [1, 2], [1, 2], [0, 10])
        repo.skill_states = [
            models.SkillState("P1", "Archer", "ArA001", "OwnedJob", "主動", 1, "Y", None, None, "", ""),
            models.SkillState("P1", "Archer", "GeA001", "OwnedGeneral", "主動", 1, "Y", None, None, "", ""),
        ]
        logic = Logic(repo)

        log = logic._check_level_up(player)
        self.assertIsNotNone(log)
        notices = logic.pop_pending_notifications()
        self.assertTrue(notices)
        self.assertTrue(
            notices[-1].get("no_skill_message") == "本次未獲得新技能"
            or bool(notices[-1].get("skills"))
        )

    def test_personal_extra_draw_does_not_advance_home_status(self):
        repo = FakeRepo()
        player = self._make_player()
        repo.players = [player]
        repo.monsters = [
            models.Monster("M1", "", "Slime", "", "易", "Run", 2, 3, 1),
        ]
        logic = Logic(repo)

        ok, _msg = logic.create_personal_extra_task(week=3, player_name="P1", monster_id="M1")
        self.assertTrue(ok)
        self.assertEqual(repo.home_updates, [])

    def test_death_penalty_pushes_notification(self):
        repo = FakeRepo()
        player = self._make_player()
        player.hp_current = 1
        task = self._make_task()
        task.fail_hp = -10
        repo.players = [player]
        repo.tasks = [task]
        logic = Logic(repo)

        logic.fail_task(task, player)
        notices = logic.pop_pending_notifications()
        self.assertTrue(any(n.get("kind") == "death" for n in notices))

    def test_levelup_skill_pool_all_jobs_can_grant_job_and_general_skills(self):
        job_cases = [
            ("弓箭手", "ArA101", "MaA999", "Ar"),
            ("法師", "MaA101", "PrA999", "Ma"),
            ("牧師", "PrA101", "SwA999", "Pr"),
            ("劍士", "SwA101", "ThA999", "Sw"),
            ("盜賊", "ThA101", "ArA999", "Th"),
        ]

        for player_job, own_skill_id, other_skill_id, skill_job_code in job_cases:
            with self.subTest(player_job=player_job):
                repo = FakeRepo()
                player = models.PlayerState(
                    name="P1",
                    job=player_job,
                    level=1,
                    exp=0,
                    hp_current=10,
                    mp_current=5,
                    hp_max=10,
                    mp_max=5,
                )
                repo.skill_states = [
                    models.SkillState("P1", skill_job_code, own_skill_id, "JobSkill", "主動", 1, "N", None, None, "", ""),
                    models.SkillState("P1", "Ge", "GeA010", "GeneralSkill", "主動", 1, "N", None, None, "", ""),
                    models.SkillState("P1", "Other", other_skill_id, "OtherJob", "主動", 1, "N", None, None, "", ""),
                ]
                logic = Logic(repo)

                granted = logic._grant_random_job_skills(player, 10)
                granted_ids = {s.skill_id for s in granted}

                self.assertIn(own_skill_id, granted_ids)
                self.assertIn("GeA010", granted_ids)
                self.assertNotIn(other_skill_id, granted_ids)

    def test_levelup_backfills_missing_skill_rows_for_legacy_save(self):
        repo = FakeRepo()
        player = models.PlayerState(
            name="P1",
            job="法師",
            level=1,
            exp=0,
            hp_current=10,
            mp_current=5,
            hp_max=10,
            mp_max=5,
        )
        # Legacy data: only base skills exist, no disabled candidate rows.
        repo.skill_states = [
            models.SkillState("P1", "Ge", "GeA001", "Base1", "主動", 0, "Y", None, None, "", ""),
            models.SkillState("P1", "Ge", "GeA002", "Base2", "主動", 0, "Y", None, None, "", ""),
        ]
        def _pool(code):
            if code == "Ma":
                return [models.SkillState("", "Ma", "MaA101", "MageSkill", "主動", 1, "N", None, None, "", "")]
            if code == "Ge":
                return [models.SkillState("", "Ge", "GeA010", "GeneralSkill", "主動", 1, "N", None, None, "", "")]
            return []
        repo.get_job_skill_pool = _pool
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 2)
        granted_ids = {s.skill_id for s in granted}

        self.assertIn("MaA101", granted_ids)
        self.assertIn("GeA010", granted_ids)
        self.assertTrue(any(s.skill_id == "MaA101" for s in repo.added_skill_states))

    def test_levelup_with_decorated_job_label_can_still_grant_job_skill(self):
        repo = FakeRepo()
        player = models.PlayerState(
            name="P1",
            job="法師(男)",
            level=1,
            exp=0,
            hp_current=10,
            mp_current=5,
            hp_max=10,
            mp_max=5,
        )
        repo.skill_states = [
            models.SkillState("P1", "Ge", "GeA001", "Base1", "主動", 0, "Y", None, None, "", ""),
            models.SkillState("P1", "Ge", "GeA002", "Base2", "主動", 0, "Y", None, None, "", ""),
        ]

        def _pool(code):
            if code in {"Ma", "法師"}:
                return [models.SkillState("", "Ma", "MaA201", "MageSkill", "主動", 1, "N", None, None, "", "")]
            if code in {"Ge", "通用"}:
                return [models.SkillState("", "Ge", "GeA010", "GeneralSkill", "主動", 1, "N", None, None, "", "")]
            return []

        repo.get_job_skill_pool = _pool
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 2)
        granted_ids = {s.skill_id for s in granted}
        self.assertIn("MaA201", granted_ids)

    def test_complete_task_is_idempotent_when_current_task_already_done(self):
        repo = FakeRepo()
        player = self._make_player()
        task = self._make_task(exp=11)
        done_task = self._make_task(exp=11)
        done_task.status = "擊殺"
        repo.players = [player]
        repo.tasks = [done_task]
        logic = Logic(repo)

        logic.complete_task(task, player, outcome="perfect")

        self.assertEqual(player.exp, 0)

    def test_levelup_skill_grant_falls_back_to_append_when_update_fails(self):
        repo = FakeRepo()
        repo.force_skill_update_fail = True
        player = self._make_player()
        repo.skill_states = [
            models.SkillState("P1", "Ar", "ArA101", "JobSkill", "主動", 1, "N", None, None, "", ""),
            models.SkillState("P1", "Ge", "GeA010", "GeneralSkill", "主動", 1, "N", None, None, "", ""),
        ]
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 1)

        self.assertTrue(granted)
        self.assertTrue(any(s.player == "P1" and s.enabled == "Y" for s in repo.added_skill_states))

    def test_levelup_skill_grant_ultimate_fallback_uses_any_disabled_player_skill(self):
        repo = FakeRepo()
        player = self._make_player()
        repo.skill_states = [
            models.SkillState("P1", "Other", "XXA001", "FallbackSkill", "主動", 1, "N", None, None, "", ""),
        ]
        repo.get_job_skill_pool = lambda _code: []
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 1)

        self.assertEqual(len(granted), 1)
        self.assertEqual(granted[0].skill_id, "XXA001")

    def test_levelup_skill_grant_cross_player_template_fallback(self):
        repo = FakeRepo()
        player = self._make_player()
        repo.skill_states = [
            models.SkillState("P2", "Ar", "ArA777", "TemplateSkill", "主動", 1, "N", None, None, "", ""),
        ]
        repo.get_job_skill_pool = lambda _code: []
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 1)

        self.assertEqual(len(granted), 1)
        self.assertEqual(granted[0].skill_id, "ArA777")

    def test_levelup_skill_grant_builtin_id_fallback(self):
        repo = FakeRepo()
        player = self._make_player()
        repo.skill_states = []
        repo.get_job_skill_pool = lambda _code: []
        logic = Logic(repo)

        granted = logic._grant_random_job_skills(player, 1)

        self.assertEqual(len(granted), 1)
        self.assertTrue(granted[0].skill_id.startswith("Ar") or granted[0].skill_id.startswith("Ge"))


if __name__ == "__main__":
    unittest.main()
