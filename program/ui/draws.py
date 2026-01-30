"""Weekly draw page."""

import streamlit as st

from ui import get_logic_state


def render() -> None:
    st.header("週結算")
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
            "BOSS編號": map_info.boss_id,
            "地圖進度": f"{map_progress}/{map_info.week}",
            "BOSS階段": "是" if boss_stage else "否",
            "BOSS結算": "已完成" if boss_settled else "未完成",
        }
    )

    bosses = logic.repo.get_bosses()
    boss = next((b for b in bosses if b.boss_id == map_info.boss_id), None)
    if boss_stage and not boss:
        st.warning("已進入 BOSS 階段，但找不到對應 BOSS 資料，請確認地圖表 BOSS 編號與 BOSS 表一致。")
    if boss and boss_stage:
        st.subheader("BOSS 資訊")
        st.write(
            {
                "名稱": boss.name,
                "需累計運動時數": boss.required_hours,
                "BOSS指定任務": boss.required_tasks,
                "章節通關獎勵": boss.clear_reward,
                "額外EXP每小時": boss.extra_exp_per_hour,
                "最後一擊獎勵": boss.last_hit_reward,
            }
        )
        st.subheader("BOSS 結算")
        if "boss_result" in st.session_state:
            st.table(st.session_state["boss_result"])
            st.info("已完成 BOSS 結算。請回到本頁下方點「每週結算」進入下一週並抽卡。")
        elif boss_settled:
            results = logic.get_boss_settlement_results(boss.boss_id, boss_week)
            if results:
                st.table([{"玩家": name, "獲得EXP": exp} for name, exp in results.items()])
            st.info("已完成 BOSS 結算。請回到本頁下方點「每週結算」進入下一週並抽卡。")
        if boss_week:
            st.caption(f"BOSS 回合：{boss_week}")
        if boss_settled:
            st.info("本週 BOSS 已結算。")
            has_choice = False
            checker = getattr(logic, "has_map_choice_for_week", None)
            if checker:
                has_choice = checker(boss_week or draw_week, map_info.map_id)
            if not has_choice:
                st.subheader("地圖選擇")
                col_next, col_replay = st.columns(2)
                with col_next:
                    if st.button("進入下一張地圖"):
                        success, message = logic.apply_boss_map_choice(
                            map_info, boss_week or draw_week, "NEXT"
                        )
                        if success:
                            st.success(message)
                            st.session_state.pop("boss_result", None)
                            st.session_state.pop("last_refresh", None)
                            st.rerun()
                        else:
                            st.warning(message)
                with col_replay:
                    if st.button("同一張地圖再玩一次"):
                        success, message = logic.apply_boss_map_choice(
                            map_info, boss_week or draw_week, "REPLAY"
                        )
                        if success:
                            st.success(message)
                            st.session_state.pop("boss_result", None)
                            st.session_state.pop("last_refresh", None)
                            st.rerun()
                        else:
                            st.warning(message)
            else:
                st.caption("已完成地圖選擇，可進行每週結算。")
        elif not logic.players:
            st.info("無玩家資料，無法結算。")
        else:
            with st.form("boss_settlement"):
                hours_inputs = {}
                task_inputs = {}
                for p in logic.players:
                    hours_inputs[p.name] = st.number_input(
                        f"{p.name} 本週運動時數",
                        min_value=0.0,
                        step=0.5,
                        value=0.0,
                    )
                    task_inputs[p.name] = st.checkbox(f"{p.name} 已完成指定任務", value=False)
                last_hit_options = ["無"] + [p.name for p in logic.players]
                last_hit = st.selectbox("最後一擊玩家", options=last_hit_options)
                submitted = st.form_submit_button("結算 BOSS")
                if submitted:
                    last_hit_player = None if last_hit == "無" else last_hit
                    success, message, detail = logic.resolve_boss_week(
                        boss,
                        boss_week or draw_week,
                        hours_by_player=hours_inputs,
                        tasks_done_by_player=task_inputs,
                        last_hit_player=last_hit_player,
                    )
                    if success:
                        st.success(message)
                        results = detail.get("exp_by_player", {})
                        st.session_state["boss_result"] = [
                            {"玩家": name, "獲得EXP": exp} for name, exp in results.items()
                        ]
                        st.session_state.pop("last_refresh", None)
                        st.rerun()
                    else:
                        st.warning(message)

    st.subheader("本週流程")
    already_event = logic.has_drawn_event(draw_week)
    already_monsters = logic.has_drawn_monsters(draw_week)
    if already_event and already_monsters:
        draw_week = base_week + 1
        already_event = logic.has_drawn_event(draw_week)
        already_monsters = logic.has_drawn_monsters(draw_week)
    settled = already_event and already_monsters
    if st.button("每週結算（抽事件 + 抽怪物 + 重置技能）", disabled=settled):
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
        codes = [c.strip() for c in event.effect_code.split(",") if c.strip()]
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
