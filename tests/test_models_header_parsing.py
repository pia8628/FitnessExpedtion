import unittest

from domain.models import Task


class ModelsHeaderParsingTests(unittest.TestCase):
    def test_task_status_header_with_parentheses_is_parsed(self):
        rows = [
            [
                "怪物ID",
                "玩家",
                "怪物名稱",
                "難度",
                "任務內容",
                "開始日",
                "截止日",
                "狀態(成功/失敗/進行中)",
                "成功EXP",
                "失敗-HP",
            ],
            ["M1", "P1", "Slime", "E", "Run", "2026-02-27", "2026-02-28", "擊殺", "10", "-1"],
        ]
        tasks = Task.from_rows(rows)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].status, "擊殺")


if __name__ == "__main__":
    unittest.main()
