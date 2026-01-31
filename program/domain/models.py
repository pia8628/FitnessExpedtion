"""
Lightweight data structures used across domain logic.
Parsing helpers convert worksheet rows into structured objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PlayerState:
    name: str
    job: str
    level: int
    exp: int
    hp_current: int
    mp_current: int
    hp_max: int
    mp_max: int
    skill_summary: str = ""
    penalty_weeks: int = 0

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["PlayerState"]:
        results: List[PlayerState] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}
        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        def parse_int(value: str, default: int = 0) -> int:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return int(float(text))
            except Exception:
                return default

        def parse_current_max(cell: str) -> tuple[int, int]:
            if not cell:
                return 0, 0
            text = str(cell)
            if "/" in text:
                cur, max_v = text.split("/", 1)
                return parse_int(cur), parse_int(max_v)
            return parse_int(text), 0
        for r in data:
            if not r or len(r) <= 1:
                continue
            try:
                hp_cell = get_value(r, ["HP", "HP當前"])
                mp_cell = get_value(r, ["MP", "MP當前"])
                hp_current, hp_max_from_cell = parse_current_max(hp_cell)
                mp_current, mp_max_from_cell = parse_current_max(mp_cell)
                results.append(
                    PlayerState(
                        name=get_value(r, ["玩家"]),
                        job=get_value(r, ["職業"]),
                        level=parse_int(get_value(r, ["等級"])),
                        exp=parse_int(get_value(r, ["EXP"])),
                        hp_current=parse_int(get_value(r, ["HP當前"]), hp_current),
                        mp_current=parse_int(get_value(r, ["MP當前"]), mp_current),
                        hp_max=parse_int(get_value(r, ["HP上限"]), hp_max_from_cell),
                        mp_max=parse_int(get_value(r, ["MP上限"]), mp_max_from_cell),
                        skill_summary=get_value(r, ["技能摘要"]),
                        penalty_weeks=parse_int(
                            get_value(
                                r,
                                ["MP歸零剩餘週數", "MP歸零剩餘", "懲罰剩餘週數", "懲罰週數"],
                            )
                        ),
                    )
                )
            except Exception:
                continue
        return results


@dataclass
class Task:
    monster_id: str
    player: str
    name: str
    difficulty: str
    content: str
    start_date: Optional[str]
    deadline: Optional[str]
    status: str
    success_exp: int = 0
    fail_hp: int = 0
    time_limit_days: Optional[int] = None

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["Task"]:
        results: List[Task] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}
        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        def parse_int(value: str, default: int = 0) -> int:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return int(float(text))
            except Exception:
                return default
        for r in data:
            if not r or len(r) <= 1:
                continue
            try:
                results.append(
                    Task(
                        monster_id=get_value(r, ["怪物ID"]),
                        player=get_value(r, ["玩家"]),
                        name=get_value(r, ["怪物名稱"]),
                        difficulty=get_value(r, ["難度"]),
                        content=get_value(r, ["任務內容"]),
                        start_date=get_value(r, ["開始日"]),
                        deadline=get_value(r, ["截止日"]),
                        status=get_value(r, ["狀態", "狀態(?/??/??)"]),
                        success_exp=parse_int(get_value(r, ["成功EXP"])),
                        fail_hp=parse_int(get_value(r, ["失敗-HP"])),
                        time_limit_days=(
                            parse_int(get_value(r, ["時限(天)"]), 0)
                            if get_value(r, ["時限(天)"])
                            else None
                        ),
                    )
                )
            except Exception:
                continue
        return results


@dataclass
class LogEntry:
    date: str
    week: str
    player: str
    type_: str
    code: str
    name: str
    desc: str
    target: str
    delta_hp: int
    delta_mp: int
    delta_exp: int
    hp: int
    mp: int
    exp: int

    def to_row(self) -> List[str]:
        return [
            self.date,
            self.week,
            self.player,
            self.type_,
            self.code,
            self.name,
            self.desc,
            self.target,
            str(self.delta_hp),
            str(self.delta_mp),
            str(self.delta_exp),
            str(self.hp),
            str(self.mp),
            str(self.exp),
        ]


@dataclass
class Event:
    event_id: str
    category: str
    name: str
    effect_code: str
    description: str
    note: str

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["Event"]:
        results: List[Event] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}

        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        for r in data:
            if not r or len(r) <= 1:
                continue
            results.append(
                Event(
                    event_id=get_value(r, ["事件編號"]),
                    category=get_value(r, ["類型", "事件類型"]),
                    name=get_value(r, ["事件名稱", "名稱"]),
                    effect_code=get_value(r, ["效果代碼"]),
                    description=get_value(r, ["敘述", "事件敘述"]),
                    note=get_value(r, ["說明", "事件影響(數值)", "備註"]),
                )
            )
        return results


@dataclass
class Monster:
    monster_id: str
    category: str
    name: str
    description: str
    difficulty: str
    content: str
    time_limit_days: int
    success_exp: int
    fail_hp: int

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["Monster"]:
        results: List[Monster] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}

        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        def parse_int(value: str, default: int = 0) -> int:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return int(float(text))
            except Exception:
                return default

        for r in data:
            if not r or len(r) <= 1:
                continue
            results.append(
                Monster(
                    monster_id=get_value(r, ["怪物編號"]),
                    category=get_value(r, ["分類"]),
                    name=get_value(r, ["怪物名稱", "名稱"]),
                    description=get_value(r, ["敘述"]),
                    difficulty=get_value(r, ["怪物等級", "怪物難度", "等級(易/中/難)", "難度"]),
                    content=get_value(r, ["任務內容"]),
                    time_limit_days=parse_int(get_value(r, ["時限(天)"])),
                    success_exp=parse_int(get_value(r, ["成功EXP"])),
                    fail_hp=parse_int(get_value(r, ["失敗HP", "失敗-HP"])),
                )
            )
        return results


@dataclass
class SkillState:
    player: str
    job: str
    skill_id: str
    name: str
    kind: str
    mp_cost: int
    enabled: str
    total_uses: Optional[int]
    remaining: Optional[int]
    reset_rule: str
    description: str

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["SkillState"]:
        results: List[SkillState] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}

        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        def parse_int(value: str) -> Optional[int]:
            if value is None:
                return None
            text = str(value).strip()
            if not text:
                return None
            try:
                return int(float(text))
            except Exception:
                return None

        for r in data:
            if not r or len(r) <= 1:
                continue
            total_uses = parse_int(get_value(r, ["每週可用總次數", "每週可用次數"]))
            remaining = parse_int(get_value(r, ["剩餘次數"]))
            if remaining is None and total_uses is not None:
                remaining = total_uses
            desc = get_value(r, ["技能效果說明", "技能敘述", "技能描述", "敘述"])
            if desc.startswith("#ERROR"):
                desc = ""
            results.append(
                SkillState(
                    player=get_value(r, ["玩家", "角色", "玩家名稱", "使用者"]),
                    job=get_value(r, ["職業"]),
                    skill_id=get_value(r, ["技能ID", "技能編碼"]),
                    name=get_value(r, ["技能名稱"]),
                    kind=get_value(r, ["主被動"]),
                    mp_cost=parse_int(get_value(r, ["MP消耗", "消耗MP"])) or 0,
                    enabled=get_value(r, ["啟用狀態"]),
                    total_uses=total_uses,
                    remaining=remaining,
                    reset_rule=get_value(r, ["重置規則"]),
                    description=desc,
                )
            )
        return results


@dataclass
class MapInfo:
    map_id: str
    name: str
    week: int
    difficulty_count: int
    easy_rate: float
    medium_rate: float
    hard_rate: float
    boss_id: str

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["MapInfo"]:
        results: List[MapInfo] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}

        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return str(row[idx]).strip()
            return str(default).strip()

        def parse_int(value: str, default: int = 0) -> int:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return int(float(text))
            except Exception:
                return default

        def parse_float(value: str, default: float = 0.0) -> float:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return float(text)
            except Exception:
                return default

        for r in data:
            if not r or len(r) <= 1:
                continue
            results.append(
                MapInfo(
                    map_id=get_value(r, ["地圖編號"]),
                    name=get_value(r, ["地圖名稱"]),
                    week=parse_int(get_value(r, ["週數"])),
                    difficulty_count=parse_int(get_value(r, ["地圖難度"])),
                    easy_rate=parse_float(get_value(r, ["Easy機率"])),
                    medium_rate=parse_float(get_value(r, ["Medium機率"])),
                    hard_rate=parse_float(get_value(r, ["Hard機率"])),
                    boss_id=get_value(r, ["BOSS編號"]),
                )
            )
        return results


@dataclass
class BossInfo:
    boss_id: str
    name: str
    required_hours: float
    required_tasks: str
    clear_reward: int
    extra_exp_per_hour: float
    last_hit_reward: int

    @staticmethod
    def from_rows(rows: List[List[str]]) -> List["BossInfo"]:
        results: List[BossInfo] = []
        if not rows:
            return results
        header, *data = rows
        col = {name: idx for idx, name in enumerate(header)}

        def get_value(row: List[str], names: List[str], default: str = "") -> str:
            for name in names:
                idx = col.get(name)
                if idx is not None and idx < len(row):
                    return row[idx]
            return default

        def parse_int(value: str, default: int = 0) -> int:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return int(float(text))
            except Exception:
                return default

        def parse_float(value: str, default: float = 0.0) -> float:
            if value is None:
                return default
            text = str(value).strip()
            if not text:
                return default
            try:
                return float(text)
            except Exception:
                return default

        for r in data:
            if not r or len(r) <= 1:
                continue
            results.append(
                BossInfo(
                    boss_id=get_value(r, ["BOSS編號"]),
                    name=get_value(r, ["名稱"]),
                    required_hours=parse_float(get_value(r, ["需累計運動時數"])),
                    required_tasks=get_value(r, ["BOSS指定任務"]),
                    clear_reward=parse_int(get_value(r, ["章節通關獎勵"])),
                    extra_exp_per_hour=parse_float(get_value(r, ["額外EXP每小時"])),
                    last_hit_reward=parse_int(get_value(r, ["最後一擊獎勵"])),
                )
            )
        return results
