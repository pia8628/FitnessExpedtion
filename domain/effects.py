"""
Event effect mapping: code -> handler.

Handlers should be pure functions: (context) -> delta/state updates.
Context (dict) suggestion:
- players: list of PlayerState
- tasks: list of Task
- flags: runtime flags (e.g., outdoor_photo=True, team_combo_used=True)
Return: optional dict of updates; unknown codes no-op.
"""

from __future__ import annotations

from typing import Callable, Dict, Any

from utils import validators


def handle_noop(context: Dict[str, Any]) -> Dict[str, Any]:
    return {}


def all_mp_plus_one(context: Dict[str, Any]) -> Dict[str, Any]:
    players = context.get("players", [])
    for p in players:
        p.mp_current = validators.clamp(p.mp_current + 1, 0, p.mp_max)
    return {"players": players}


def all_hp_plus_two(context: Dict[str, Any]) -> Dict[str, Any]:
    players = context.get("players", [])
    for p in players:
        p.hp_current = validators.clamp(p.hp_current + 2, 0, p.hp_max)
    return {"players": players}


def bonus_exp_if_outdoor_photo(context: Dict[str, Any]) -> Dict[str, Any]:
    if not context.get("outdoor_photo"):
        return {}
    players = context.get("players", [])
    for p in players:
        p.exp += 2
    return {"players": players}


def bonus_exp_if_outdoor_exercise(context: Dict[str, Any]) -> Dict[str, Any]:
    if not context.get("outdoor_exercise"):
        return {}
    players = context.get("players", [])
    for p in players:
        p.exp += 2
    return {"players": players}


def monster_time_minus_one(context: Dict[str, Any]) -> Dict[str, Any]:
    tasks = context.get("tasks", [])
    for t in tasks:
        if hasattr(t, "time_bonus"):
            t.time_bonus -= 1  # type: ignore
        else:
            t.time_bonus = -1  # type: ignore
    return {"tasks": tasks}


EFFECT_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "ALL_MP+1": all_mp_plus_one,
    "ALL_HP+2": all_hp_plus_two,
    "IF_OUTDOOR_PHOTO_THEN_EXP+2": bonus_exp_if_outdoor_photo,
    "IF_OUTDOOR_EXERCISE_THEN_EXP+2": bonus_exp_if_outdoor_exercise,
    "ALL_MONSTER_LV+1": handle_noop,  # handled at draw time
    "BONUS_EXP+3": handle_noop,  # handled at reward calc
    "MONSTER_TIME-1_DAY": monster_time_minus_one,
    "REST_MP_RECOVERY_DISABLED": handle_noop,
    "FIRST_EXERCISE_EXP=1": handle_noop,
    "CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5": handle_noop,
    "EXTRA_WORKOUT_MVP_EXP+5": handle_noop,
    "REDRAW_ALL_MONSTERS": handle_noop,
    "IF_TEAM_COMBO_THEN_ALL_EXP+3": handle_noop,
}


def dispatch(code: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    return EFFECT_HANDLERS.get(code, handle_noop)
