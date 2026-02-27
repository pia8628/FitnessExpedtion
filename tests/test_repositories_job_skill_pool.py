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


class _FakeClient:
    def __init__(self, header, data):
        self._header = header
        self._data = data

    def read_rows_with_header(self, _sheet_name):
        return self._header, self._data


class JobSkillPoolParsingTests(unittest.TestCase):
    def test_parses_with_positional_fallback_when_header_unusable(self):
        # A~I: skill_id, job, name, kind, mp, value, total, reset, desc
        header = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        data = [
            ["MaA101", "法師", "火球", "主動", "2", "", "1", "週重置", "造成火焰傷害"],
            ["ArA101", "弓箭手", "穿透箭", "主動", "1", "", "2", "週重置", "造成穿透傷害"],
        ]
        repo = Repositories(_FakeClient(header, data))

        skills = repo.get_job_skill_pool("Ma")
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].skill_id, "MaA101")
        self.assertEqual(skills[0].name, "火球")

    def test_parses_general_alias(self):
        header = ["技能ID", "職業", "技能名稱", "主被動", "MP消耗", "數值", "每週可用次數", "重置規則", "技能描述"]
        data = [
            ["GeA010", "通用", "健行", "主動", "0", "", "1", "週重置", "通用技能"],
        ]
        repo = Repositories(_FakeClient(header, data))

        skills = repo.get_job_skill_pool("Ge")
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].skill_id, "GeA010")

    def test_matches_by_skill_prefix_when_job_column_is_unexpected(self):
        header = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        data = [
            ["MaA105", "UnknownJob", "Meteor", "主動", "3", "", "1", "週重置", "Boom"],
        ]
        repo = Repositories(_FakeClient(header, data))

        skills = repo.get_job_skill_pool("Ma")
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].skill_id, "MaA105")


if __name__ == "__main__":
    unittest.main()
