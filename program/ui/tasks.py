"""Tasks page: draw events/monsters, mark complete/fail."""

import streamlit as st

from ui import get_logic_state


def render() -> None:
    st.header("任務")
    try:
        logic = get_logic_state()
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        return

    st.subheader("事件任務")
    week = logic.get_last_week_from_logs()
    event = logic.get_event_for_week(week) if week > 0 else None
    codes = []
    if event and event.effect_code:
        codes = [c.strip() for c in event.effect_code.split(",") if c.strip()]

    if not codes:
        st.info("本周無事件任務")
    else:
        if "IF_OUTDOOR_EXERCISE_THEN_EXP+2" in codes:
            st.write("戶外運動：本週有戶外運動即可完成，完成後全員 EXP +2。")
            if st.button("完成任務", key="outdoor_exercise"):
                success, message = logic.complete_outdoor_exercise_event(week)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)
        if "IF_OUTDOOR_PHOTO_THEN_EXP+2" in codes:
            st.write("戶外照片：本週有戶外照片即可完成，完成後全員 EXP +2。")
            if st.button("完成任務", key="outdoor_photo"):
                success, message = logic.complete_outdoor_photo_event(week)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)
        if "EXTRA_WORKOUT_MVP_EXP+5" in codes:
            st.write("額外運動：選一位玩家完成額外運動，個人 EXP +5。")
            options = [p.name for p in logic.players] if logic.players else []
            selected = st.selectbox("選擇玩家", options=options, key="extra_workout_player")
            if st.button("完成額外運動", key="extra_workout"):
                success, message = logic.complete_extra_workout_event(week, selected)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)

    st.subheader("怪物任務")
    if not logic.tasks:
        st.info("尚無任務資料。")
        return

    task_labels = [f"{t.player} - {t.name} ({t.monster_id})" for t in logic.tasks]
    selected = st.selectbox("選擇任務", options=task_labels)
    task = logic.tasks[task_labels.index(selected)]
    player = next((p for p in logic.players if p.name == task.player), None)

    st.write(
        {
            "怪物名稱": task.name,
            "難度": task.difficulty,
            "任務內容": task.content,
            "截止日": task.deadline or "",
            "狀態": task.status,
            "成功EXP": task.success_exp,
            "失敗-HP": task.fail_hp,
        }
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("完成任務"):
            if not player:
                st.error("找不到對應玩家。")
            else:
                logic.complete_task(task, player)
                st.success("已標記完成。")
                st.rerun()
    with col2:
        if st.button("任務失敗"):
            if not player:
                st.error("找不到對應玩家。")
            else:
                logic.fail_task(task, player)
                st.warning("已標記失敗。")
                st.rerun()
    with col3:
        if st.button("檢查逾時"):
            logic.mark_overdue_tasks()
            st.info("已檢查逾時任務。")
            st.rerun()
