"""Weekly draw page."""

import streamlit as st

from ui import get_logic_state, render_header


def render() -> None:
    render_header(page_title="週結算")
    try:
        logic = get_logic_state()
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        return

    maps = logic.repo.get_maps()
    if not maps:
        st.info("地圖表無資料。")
        return

    maps_sorted = sorted(maps, key=lambda m: m.week)
    next_week = logic.get_next_week()
    home_week, home_map_id = logic.repo.get_home_status()
    base_week = home_week if home_week and home_week > 0 else next_week
    draw_week = base_week
    boss_week = base_week if base_week > 0 else logic.get_last_week_from_logs()
    map_info = None
    if home_map_id:
        map_info = next((m for m in maps_sorted if m.map_id == home_map_id), None)
    if map_info is None:
        map_info = next((m for m in maps_sorted if m.week == draw_week), None)
    if map_info is None:
        map_info = max(
            (m for m in maps_sorted if m.week <= draw_week),
            key=lambda m: m.week,
            default=maps_sorted[-1],
        )
    map_progress = logic.get_map_progress(map_info.map_id) if map_info else 0
    boss_stage = logic.is_boss_stage(map_info) if map_info else False
    boss_settled = logic.has_boss_settlement_for_week(boss_week) if boss_week else False
    if not boss_settled and map_info and map_info.boss_id:
        boss_settled = logic.has_boss_settlement_for_boss(map_info.boss_id, boss_week)

    st.subheader("地圖資訊")
    st.write(
        {
            "回合": draw_week,
            "地圖名稱": map_info.name,
            "地圖難度": map_info.difficulty_count,
            "Easy機率": map_info.easy_rate,
            "Medium機率": map_info.medium_rate,
            "Hard機率": map_info.hard_rate,
            "地圖進度": f"{map_progress}/{map_info.week}",
        }
    )

    st.subheader("本週流程")
    already_event = logic.has_drawn_event(draw_week)
    already_monsters = logic.has_drawn_monsters(draw_week)
    if already_event and already_monsters:
        draw_week = base_week + 1
        already_event = logic.has_drawn_event(draw_week)
        already_monsters = logic.has_drawn_monsters(draw_week)
    settled = already_event and already_monsters
    boss_blocked = boss_stage and not boss_settled
    if boss_blocked:
        st.warning("地圖已進入 BOSS 階段，請先完成 BOSS 結算與地圖選擇。")
    pending_tasks = logic.count_incomplete_tasks_for_week(draw_week)
    if st.button(
        "每週結算（抽事件 + 抽怪物 + 重置技能）", disabled=settled or boss_blocked
    ):
        if pending_tasks > 0:
            st.session_state["confirm_settle_week"] = draw_week
        else:
            success, message, detail = logic.settle_week(draw_week, map_info)
            if success:
                event = detail.get("event")
                created = detail.get("tasks")
                map_progress = detail.get("map_progress", map_progress)
                boss_stage = logic.is_boss_stage(map_info)
                if event:
                    st.session_state["last_event"] = event
                if created:
                    st.session_state["last_drawn_tasks"] = created
                st.session_state.pop("boss_result", None)
                st.session_state.pop("last_refresh", None)
                st.success(message)
                st.rerun()
            else:
                st.warning(message)

    if st.session_state.get("confirm_settle_week") == draw_week:
        st.warning(f"本週仍有 {pending_tasks} 筆未完成任務，確認後將全部判定為失敗。")
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("確認結算並判定失敗", key="confirm_settle"):
                logic.fail_incomplete_tasks_for_week(draw_week)
                st.session_state.pop("confirm_settle_week", None)
                success, message, detail = logic.settle_week(draw_week, map_info)
                if success:
                    event = detail.get("event")
                    created = detail.get("tasks")
                    map_progress = detail.get("map_progress", map_progress)
                    boss_stage = logic.is_boss_stage(map_info)
                    if event:
                        st.session_state["last_event"] = event
                    if created:
                        st.session_state["last_drawn_tasks"] = created
                    st.session_state.pop("boss_result", None)
                    st.session_state.pop("last_refresh", None)
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)
        with col_cancel:
            if st.button("取消", key="cancel_settle"):
                st.session_state.pop("confirm_settle_week", None)

    event = None
    if "last_event" in st.session_state:
        event = st.session_state["last_event"]
        event_type = f"({event.category})" if event.category else ""
        st.info(f"本次事件：{event.name}{event_type}")
        if event.description:
            st.write(f"事件敘述：{event.description}")
        if event.note:
            st.write(f"說明：{event.note}")
    elif already_event:
        event = logic.get_event_for_week(draw_week)
        if event:
            event_type = f"({event.category})" if event.category else ""
            st.info(f"本次事件：{event.name}{event_type}")
            if event.description:
                st.write(f"事件敘述：{event.description}")
            if event.note:
                st.write(f"說明：{event.note}")
        else:
            st.info("本週已抽事件。")

    if event and event.effect_code:
        codes = logic.parse_event_codes(event.effect_code)
        if "CHOICE_MONSTER_LV-1_OR_LV+1_BONUS_EXP+5" in codes:
            st.subheader("事件選擇")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("選 A：怪物難度 -1"):
                    success, message = logic.apply_choice_monster_event(draw_week, "A")
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.warning(message)
            with col_b:
                if st.button("選 B：怪物難度 +1 並成功 +5 EXP"):
                    success, message = logic.apply_choice_monster_event(draw_week, "B")
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.warning(message)

    if "last_drawn_tasks" in st.session_state:
        st.write("本次抽出的任務")
        st.table(
            [
                {
                    "玩家": t.player,
                    "怪物": t.name,
                    "難度": t.difficulty,
                    "任務": t.content,
                    "截止日": t.deadline,
                }
                for t in st.session_state["last_drawn_tasks"]
            ]
        )
    elif already_monsters:
        st.info("本週已抽怪物。")

    st.caption("進行本週抽卡與週結算流程。")
    st.caption("若仍有未完成任務，可先確認失敗再結算。")

