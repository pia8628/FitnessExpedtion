"""Skills page."""

import streamlit as st

from ui import get_logic_state


def render() -> None:
    st.header("技能")
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

    actor_name = st.selectbox("使用者", options=actor_names)
    skill_states = st.session_state["skill_states"]
    actor_skills = [
        s
        for s in skill_states
        if s.player == actor_name and s.enabled.upper() == "Y" and s.kind.upper() in {"A", "主動"}
    ]

    if not actor_skills:
        st.info("此玩家沒有可用主動技能。")
        return

    skill_label_map = {f"{s.name} ({s.skill_id})": s for s in actor_skills}
    skill_label = st.selectbox("技能", options=list(skill_label_map.keys()))
    skill = skill_label_map[skill_label]

    requires_target = skill.skill_id in {"GeA001", "PrA001", "ArA001"}
    requires_task = skill.skill_id in {"MaA001", "ThA001"}

    actor = next((p for p in logic.players if p.name == actor_name), None)
    if actor:
        st.caption(f"{actor.name} HP {actor.hp_current}/{actor.hp_max}｜MP {actor.mp_current}/{actor.mp_max}")

    if skill.description:
        st.write(f"技能說明：{skill.description}")

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

    st.caption(
        f"MP消耗：{skill.mp_cost}｜剩餘次數：{skill.remaining if skill.remaining is not None else '不限'}"
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
