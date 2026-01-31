"""
Skill handlers: MP/usage validation and effect application.

Separate active vs passive triggers; integrate with logic layer.
"""

from __future__ import annotations

from typing import Dict, Any

from utils import validators


class SkillContext:
    """
    Lightweight context passed into skill handlers.
    """

    def __init__(
        self, actor, target=None, task=None, state=None, skill_state=None, mp_discount: int = 0, **kwargs
    ):
        self.actor = actor
        self.target = target
        self.task = task
        self.state = state
        self.skill_state = skill_state
        self.mp_discount = mp_discount
        for key, value in kwargs.items():
            setattr(self, key, value)


def apply_active(skill_id: str, context: SkillContext) -> bool:
    """
    Route to specific active skill effect.
    Basic handling:
    - 急救/治療：目標 HP+1，自己 MP-1
    - 延長時限：目標任務 +1 天（僅標記，實際截止日計算交給邏輯）
    - 弱化怪物：目標任務難度 -1 級（易/中/難）
    - 遠距支援：標記目標下一次失敗不扣 HP（flag）
    - 合體技：僅扣 MP，EXP 加成交由結算時處理
    """
    if context is None:
        raise ValueError("SkillContext is required")
    actor = context.actor
    target = context.target

    def spend_mp(cost: int) -> bool:
        if actor.mp_current < cost:
            return False
        actor.mp_current -= cost
        return True

    def get_cost(default_cost: int) -> int:
        if context.skill_state is None:
            return default_cost
        if context.skill_state.mp_cost is None:
            return default_cost
        return int(context.skill_state.mp_cost)

    if skill_id == "GeA001":  # 急救
        if not target:
            return False
        cost = max(0, get_cost(1) - context.mp_discount)
        if not spend_mp(cost):
            return False
        target.hp_current = validators.clamp(target.hp_current + 1, 0, target.hp_max)
        return True
    if skill_id == "PrA001":  # 牧師治療
        if not target:
            return False
        cost = max(0, get_cost(1) - context.mp_discount)
        if not spend_mp(cost):
            return False
        target.hp_current = validators.clamp(target.hp_current + 1, 0, target.hp_max)
        return True
    if skill_id == "ThA001":  # 延長時限
        cost = max(0, get_cost(1) - context.mp_discount)
        if not spend_mp(cost):
            return False
        if not context.task:
            return False
        # 標記額外天數，由邏輯層計算實際截止日
        setattr(context.task, "extra_days", getattr(context.task, "extra_days", 0) + 1)
        return True
    if skill_id == "MaA001":  # 弱化怪物
        cost = max(0, get_cost(2) - context.mp_discount)
        if not spend_mp(cost):
            return False
        if not context.task:
            return False
        # 降低難度一級
        difficulty_map = {"難": "中", "中": "易", "易": "易"}
        context.task.difficulty = difficulty_map.get(context.task.difficulty, context.task.difficulty)
        return True
    if skill_id == "ArA001":  # 遠距支援
        cost = max(0, get_cost(1) - context.mp_discount)
        if not spend_mp(cost):
            return False
        if target:
            setattr(target, "shield_fail", True)
            return True
        return False
    if skill_id == "GeA002":  # 合體技
        cost = max(0, get_cost(1) - context.mp_discount)
        if not spend_mp(cost):
            return False
        return True
    return False


def apply_passive(trigger: str, context) -> Dict[str, Any]:
    if context is None or context.state is None:
        return {}
    state = context.state
    actor = context.actor
    passives = state._get_player_passives(actor.name)

    if trigger == "on_complete":
        bonus_exp = 0
        bonus_mp = 0
        week_str = getattr(context, "week_str", "")
        log_data = getattr(context, "log_data", [])
        log_idx = getattr(context, "log_idx", {})
        today = getattr(context, "today", None)

        if "MaP001" in passives:
            completed_count = state._count_player_completions(
                actor.name, week_str, log_data, log_idx
            )
            completed_count += 1
            if completed_count in {2, 4}:
                bonus_mp += 1

        if "MaP003" in passives:
            if state._has_recent_skill_after_last_completion(
                actor.name, week_str, {"GeA001", "PrA001", "MaA001"}, log_data, log_idx
            ):
                bonus_exp += 1

        if "ThP001" in passives and today is not None:
            if state._last_completion_was_yesterday(
                actor.name, today, week_str, log_data, log_idx
            ):
                bonus_exp += 1

        if "ThP002" in passives:
            if not state._has_team_completion(week_str, log_data, log_idx):
                bonus_exp += 1

        if "ArP001" in passives:
            if not state._has_player_completion(actor.name, week_str, log_data, log_idx):
                bonus_exp += 1

        if "ArP002" in passives:
            deadline = state._parse_deadline(getattr(context.task, "deadline", None))
            if deadline and today is not None and (deadline - today).days <= 1:
                bonus_exp += 1

        return {"bonus_exp": bonus_exp, "bonus_mp": bonus_mp}

    if trigger == "on_combo":
        if "SwP003" in passives:
            actor.hp_current = validators.clamp(actor.hp_current + 1, 0, actor.hp_max)
            return {"hp_bonus": 1}
        return {}

    if trigger == "on_fail":
        delta_hp = getattr(context, "delta_hp", 0)
        week_str = getattr(context, "week_str", "")
        log_data = getattr(context, "log_data", [])
        log_idx = getattr(context, "log_idx", {})
        if "SwP001" in passives:
            delta_hp = max(delta_hp + 1, -1)
        if "SwP002" in passives:
            if not state._has_player_failure(actor.name, week_str, log_data, log_idx):
                delta_hp = max(delta_hp + 1, -1)
        return {"delta_hp": delta_hp}

    if trigger == "on_supported_complete":
        week_str = getattr(context, "week_str", "")
        log_data = getattr(context, "log_data", [])
        log_idx = getattr(context, "log_idx", {})
        if state._has_support_bonus(actor.name, week_str, log_data, log_idx):
            return {"bonus_exp": 1, "support_bonus": True}
        return {}

    if trigger == "on_rescued_complete":
        week_str = getattr(context, "week_str", "")
        log_data = getattr(context, "log_data", [])
        log_idx = getattr(context, "log_idx", {})
        players = getattr(context, "players", None)
        completed_player = getattr(context, "completed_player", actor)
        if players is None:
            players = getattr(state, "players", [])
        rescues = []
        if not week_str:
            return {"rescues": rescues}
        for rescuer in players:
            passives = state._get_player_passives(rescuer.name)
            if "PrP002" not in passives:
                continue
            bonus_count = 0
            rescued_target = False
            for row in log_data:
                if len(row) <= max(
                    log_idx.get("week", 0),
                    log_idx.get("player", 0),
                    log_idx.get("type", 0),
                    log_idx.get("code", 0),
                    log_idx.get("target", 0),
                ):
                    continue
                if str(row[log_idx.get("week")]).strip() != week_str:
                    continue
                if row[log_idx.get("player")] != rescuer.name:
                    continue
                if row[log_idx.get("type")] == "事件" and row[log_idx.get("code")] == "PrP002":
                    bonus_count += 1
                if (
                    row[log_idx.get("type")] == "技能"
                    and row[log_idx.get("code")] in {"GeA001", "PrA001", "ArA001"}
                    and row[log_idx.get("target")] == completed_player.name
                ):
                    rescued_target = True
            if not rescued_target or bonus_count >= 2:
                continue
            rescues.append((rescuer.name, 1, completed_player.name))
        return {"rescues": rescues}

    if trigger == "on_support_used":
        skill_id = getattr(context, "skill_id", "")
        if skill_id not in {"GeA001", "PrA001", "MaA001"}:
            return {}
        if "MaP002" in passives:
            if not state._has_skill_usage(
                actor.name,
                getattr(context, "week_str", ""),
                {"GeA001", "PrA001", "MaA001"},
                getattr(context, "log_data", []),
                getattr(context, "log_idx", {}),
            ):
                return {"mp_discount": 1}
        return {}

    if trigger == "on_event_checked":
        code = getattr(context, "event_code", "")
        if code == "REST_MP_RECOVERY_DISABLED":
            return {"rest_mp_disabled": True}
        if code == "EXTRA_WORKOUT_MVP_EXP+5":
            return {"extra_workout_bonus": 5}
        return {}

    return {}


ACTIVE_SKILLS: Dict[str, str] = {
    "GeA001": "heal",
    "GeA002": "combo",
    "MaA001": "debuff",
    "ThA001": "extend",
    "ArA001": "support",
    "PrA001": "heal_priest",
}

PASSIVE_SKILLS: Dict[str, str] = {
    "MaP001": "aura",
    "MaP002": "first_heal_discount",
    "MaP003": "heal_echo",
    "SwP001": "toughness",
    "SwP002": "first_fail_reduction",
    "SwP003": "combo_hp_up",
    "ThP001": "chain_attack",
    "ThP002": "first_complete_bonus",
    "ArP001": "first_task_bonus",
    "ArP002": "late_finish_bonus",
    "PrP001": "gentle_guidance",
    "PrP002": "empathy_feedback",
}
