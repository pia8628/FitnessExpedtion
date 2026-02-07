"""Skills page."""

import streamlit as st

from ui import get_logic_state, get_active_player, render_header


def render() -> None:
    render_header(page_title="技能")
    try:
        logic = get_logic_state()
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        return

    if not logic.players:
        st.info("尚無玩家資料。")
        return

    if st.button("重新讀取技能狀態"):
        st.session_state.pop("skill_states", None)

    if "skill_states" not in st.session_state:
        st.session_state["skill_states"] = logic.repo.get_skill_states()

    actor_names = [p.name for p in logic.players]
    tasks = logic.tasks

    active_player = get_active_player()
    if active_player and active_player in actor_names:
        actor_name = active_player
        st.caption(f"使用者：{actor_name}")
    else:
        actor_name = st.selectbox("使用者", options=actor_names)
    skill_states = st.session_state["skill_states"]
    def _is_enabled(state) -> bool:
        raw = (state.enabled or "").strip()
        if not raw:
            return True
        normalized = raw.upper()
        if normalized in {"N", "NO", "FALSE", "0"} or raw in {"否", "停用", "禁用"}:
            return False
        return True

    def _is_active_kind(state) -> bool:
        kind = (state.kind or "").strip()
        if not kind:
            return True
        normalized = kind.upper()
        if "主動" in kind or normalized in {"A", "ACTIVE"}:
            return True
        if "被動" in kind or normalized in {"P", "PASSIVE"}:
            return False
        return True

    actor_skills = [
        s
        for s in skill_states
        if s.player == actor_name and _is_enabled(s) and _is_active_kind(s)
    ]

    if not actor_skills:
        st.info("此玩家沒有可用主動技能。")
        return

    def label_for(state):
        return state.name or state.skill_id

    skill_label_map = {label_for(s): s for s in actor_skills}
    skill_label = st.selectbox("技能", options=list(skill_label_map.keys()))
    skill = skill_label_map[skill_label]

    skill_def = None
    desc_from_state = (skill.description or "").strip()
    if desc_from_state.startswith("#ERROR"):
        desc_from_state = ""
    if (not skill.name or not desc_from_state or not skill.mp_cost) and skill.skill_id:
        skill_def = logic.repo.get_skill_definition(skill.skill_id)
    if skill_def and skill_def.description and skill_def.description != skill.description:
        skill.description = skill_def.description
        logic.repo.update_skill_state(skill)

    requires_target = skill.skill_id in {"GeA001", "PrA001", "ArA001"}
    requires_task = skill.skill_id in {"MaA001", "ThA001"}

    actor = next((p for p in logic.players if p.name == actor_name), None)
    if actor:
        st.caption(f"{actor.name} HP {actor.hp_current}/{actor.hp_max}｜MP {actor.mp_current}/{actor.mp_max}")

    desc = (skill_def.description if skill_def and skill_def.description else desc_from_state)
    if desc:
        st.write(f"技能說明：{desc}")

    target_name = None
    if requires_target:
        target_name = st.selectbox("目標", options=actor_names)
        target = next((p for p in logic.players if p.name == target_name), None)
        if target:
            st.caption(f"{target.name} HP {target.hp_current}/{target.hp_max}｜MP {target.mp_current}/{target.mp_max}")

    task = None
    if requires_task:
        if tasks:
            task_labels = [f"{t.player} - {t.name} ({t.monster_id})" for t in tasks]
            selected_task = st.selectbox("任務", options=task_labels)
            task = tasks[task_labels.index(selected_task)]
        else:
            st.info("目前沒有可選任務。")

    mp_cost = skill.mp_cost if skill.mp_cost else (skill_def.mp_cost if skill_def else 0)
    remaining_display = skill.remaining
    if remaining_display is None and getattr(skill, "total_uses", None) is not None:
        remaining_display = skill.total_uses
    st.caption(
        f"MP消耗：{mp_cost}｜剩餘次數：{remaining_display if remaining_display is not None else '不限'}"
    )

    if st.button("使用技能"):
        target = None
        if target_name:
            target = next((p for p in logic.players if p.name == target_name), None)
        if not actor:
            st.error("找不到使用者。")
            return
        if requires_target and not target:
            st.error("請選擇目標。")
            return
        if requires_task and not task:
            st.error("請選擇任務。")
            return
        if skill.remaining is not None and skill.remaining <= 0:
            st.warning("技能次數不足。")
            return
        if skill_def and (not skill.mp_cost or skill.mp_cost == 0):
            skill.mp_cost = skill_def.mp_cost
        if logic.use_skill(skill.skill_id, actor, target, task, skill_state=skill):
            st.success("技能已套用。")
            st.caption(
                f"{actor.name} HP {actor.hp_current}/{actor.hp_max}｜MP {actor.mp_current}/{actor.mp_max}"
            )
            if target:
                st.caption(
                    f"{target.name} HP {target.hp_current}/{target.hp_max}｜MP {target.mp_current}/{target.mp_max}"
                )
        else:
            st.warning("技能使用失敗（MP 不足或條件不符）。")

    st.caption("選擇欲施放的技能，部分技能需選擇施放目標。")
    st.caption("合體技使用：施放完合體技後，擊敗怪物將獲得合體技的經驗值獎勵。")
    st.caption("注意 MP 消耗與剩餘次數。")

