"""Tasks page: draw events/monsters, mark complete/fail."""

import streamlit as st

from ui import get_logic_state, get_active_player


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
    if event and not logic.is_task_event(event):
        event = None
    codes = []
    if event and event.effect_code:
        codes = logic.parse_event_codes(event.effect_code)

    if not codes:
        st.info("本周無事件任務")
    else:
        if "IF_OUTDOOR_EXERCISE_THEN_EXP+2" in codes:
            st.write("戶外運動：本週有戶外運動即可完成，完成後全員 EXP +2。")
            completed = logic.has_event_completion(week, "IF_OUTDOOR_EXERCISE_THEN_EXP+2")
            if completed:
                st.caption("本週已完成戶外運動事件。")
            if st.button("完成任務", key="outdoor_exercise", disabled=completed):
                success, message = logic.complete_outdoor_exercise_event(week)
                if success:
                    st.success(message)
                    st.session_state.pop("last_refresh", None)
                    st.rerun()
                else:
                    st.warning(message)
        if "IF_OUTDOOR_PHOTO_THEN_EXP+2" in codes:
            st.write("戶外照片：本週有戶外照片即可完成，完成後全員 EXP +2。")
            completed = logic.has_event_completion(week, "IF_OUTDOOR_PHOTO_THEN_EXP+2")
            if completed:
                st.caption("本週已完成戶外照片事件。")
            if st.button("完成任務", key="outdoor_photo", disabled=completed):
                success, message = logic.complete_outdoor_photo_event(week)
                if success:
                    st.success(message)
                    st.session_state.pop("last_refresh", None)
                    st.rerun()
                else:
                    st.warning(message)
        if "EXTRA_WORKOUT_MVP_EXP+5" in codes:
            st.write("額外運動：選一位玩家完成額外運動，個人 EXP +5。")
            options = [p.name for p in logic.players] if logic.players else []
            selected = st.selectbox("選擇玩家", options=options, key="extra_workout_player")
            completed = (
                logic.has_event_completion(week, "EXTRA_WORKOUT_MVP_EXP+5", selected)
                if selected
                else False
            )
            if completed:
                st.caption("本週已完成額外運動事件。")
            if st.button("完成額外運動", key="extra_workout", disabled=completed):
                success, message = logic.complete_extra_workout_event(week, selected)
                if success:
                    st.success(message)
                    st.session_state.pop("last_refresh", None)
                    st.rerun()
                else:
                    st.warning(message)

    st.subheader("BOSS")
    maps = logic.repo.get_maps()
    if not maps:
        st.info("地圖表無資料。")
    else:
        maps_sorted = sorted(maps, key=lambda m: m.week)
        home_week, home_map_id = logic.repo.get_home_status()
        base_week = home_week if home_week and home_week > 0 else logic.get_last_week_from_logs()
        boss_week = base_week if base_week and base_week > 0 else logic.get_last_week_from_logs()
        map_info = None
        if home_map_id:
            map_info = next((m for m in maps_sorted if m.map_id == home_map_id), None)
        if map_info is None:
            map_info = next((m for m in maps_sorted if m.week == base_week), None)
        if map_info is None:
            map_info = max(
                (m for m in maps_sorted if m.week <= base_week),
                key=lambda m: m.week,
                default=maps_sorted[-1],
            )
        map_progress = logic.get_map_progress(map_info.map_id) if map_info else 0
        boss_stage = logic.is_boss_stage(map_info) if map_info else False
        boss_settled = logic.has_boss_settlement_for_week(boss_week) if boss_week else False
        if not boss_settled and map_info and map_info.boss_id:
            boss_settled = logic.has_boss_settlement_for_boss(map_info.boss_id, boss_week)

        st.write(
            {
                "回合": base_week,
                "地圖名稱": map_info.name,
                "地圖進度": f"{map_progress}/{map_info.week}",
                "BOSS編號": map_info.boss_id,
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
            st.subheader("BOSS 貢獻")
            contrib_week = boss_week or base_week
            contributions = logic.get_boss_contributions(boss.boss_id, contrib_week)
            contrib_rows = []
            total_hours = 0.0
            completed_tasks = 0
            for p in logic.players:
                record = contributions.get(p.name, {"hours": 0.0, "task_done": False})
                hours = float(record.get("hours", 0.0))
                task_done = bool(record.get("task_done", False))
                total_hours += hours
                completed_tasks += 1 if task_done else 0
                contrib_rows.append(
                    {"玩家": p.name, "時數": hours, "完成指定任務": "是" if task_done else "否"}
                )
            if contrib_rows:
                st.table(contrib_rows)
            st.caption(
                f"累計時數：{total_hours}｜完成指定任務：{completed_tasks}/{len(logic.players)}"
            )

            active_player = get_active_player()
            with st.form("boss_contrib"):
                hours_inputs = {}
                task_inputs = {}
                for p in logic.players:
                    default_hours = contributions.get(p.name, {}).get("hours", 0.0)
                    default_task = contributions.get(p.name, {}).get("task_done", False)
                    disabled = active_player is not None and p.name != active_player
                    hours_inputs[p.name] = st.number_input(
                        f"{p.name} 本週運動時數",
                        min_value=0.0,
                        step=0.5,
                        value=float(default_hours) if default_hours is not None else 0.0,
                        disabled=disabled,
                    )
                    task_inputs[p.name] = st.checkbox(
                        f"{p.name} 已完成指定任務",
                        value=bool(default_task),
                        disabled=disabled,
                    )
                if st.form_submit_button("更新貢獻"):
                    if not active_player:
                        st.warning("請先進入遊戲並選擇玩家。")
                    else:
                        success, message = logic.record_boss_contributions(
                            boss, contrib_week, hours_inputs, task_inputs, active_player=active_player
                        )
                        if success:
                            st.success(message)
                            st.session_state.pop("last_refresh", None)
                            st.rerun()
                        else:
                            st.warning(message)
            st.subheader("BOSS 結算")
            if "boss_result" in st.session_state:
                st.table(st.session_state["boss_result"])
                st.info("已完成 BOSS 結算。請進行地圖選擇。")
            elif boss_settled:
                results = logic.get_boss_settlement_results(boss.boss_id, boss_week)
                if results:
                    st.table([{"玩家": name, "獲得EXP": exp} for name, exp in results.items()])
                st.info("已完成 BOSS 結算。請進行地圖選擇。")
            elif not logic.players:
                st.info("無玩家資料，無法結算。")
            else:
                st.caption("結算將使用目前的 BOSS 貢獻資料。")
                last_hit_options = ["無"] + [p.name for p in logic.players]
                last_hit = st.selectbox("最後一擊玩家", options=last_hit_options)
                if st.button("結算 BOSS"):
                    hours_inputs = {
                        p.name: contributions.get(p.name, {}).get("hours", 0.0) for p in logic.players
                    }
                    task_inputs = {
                        p.name: contributions.get(p.name, {}).get("task_done", False)
                        for p in logic.players
                    }
                    last_hit_player = None if last_hit == "無" else last_hit
                    success, message, detail = logic.resolve_boss_week(
                        boss,
                        boss_week or base_week,
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
            if boss_week:
                st.caption(f"BOSS 回合：{boss_week}")
            if boss_settled:
                has_choice = False
                checker = getattr(logic, "has_map_choice_for_week", None)
                if checker:
                    has_choice = checker(boss_week, map_info.map_id)
                if not has_choice:
                    st.subheader("地圖選擇")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("前進下一張地圖", key="boss_next_map"):
                            success, message = logic.apply_boss_map_choice(
                                map_info, boss_week, "NEXT"
                            )
                            if success:
                                st.success(message)
                                st.session_state.pop("last_refresh", None)
                                st.rerun()
                            else:
                                st.warning(message)
                    with col_b:
                        if st.button("重玩本張地圖", key="boss_replay_map"):
                            success, message = logic.apply_boss_map_choice(
                                map_info, boss_week, "REPLAY"
                            )
                            if success:
                                st.success(message)
                                st.session_state.pop("last_refresh", None)
                                st.rerun()
                            else:
                                st.warning(message)

    st.subheader("怪物任務")
    active_player = get_active_player()
    tasks = logic.tasks
    if active_player:
        tasks = [t for t in tasks if t.player == active_player]
    if not tasks:
        st.info("尚無任務資料。")
        return

    task_labels = [f"{t.player} - {t.name} ({t.monster_id})" for t in tasks]
    selected = st.selectbox("選擇任務", options=task_labels)
    task = tasks[task_labels.index(selected)]
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

    status_done = {"✅擊殺", "☠️失敗", "?擊殺", "??失敗"}
    is_done = task.status in status_done
    if is_done:
        st.caption("此任務已完成，將在下次週結算時清除。")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("完成任務", disabled=is_done):
            if not player:
                st.error("找不到對應玩家。")
            else:
                if logic.is_task_overdue(task):
                    logic.fail_task(task, player)
                    st.warning("任務已超過截止日，判定為失敗。")
                    st.session_state.pop("last_refresh", None)
                    st.rerun()
                    return
                logic.complete_task(task, player)
                st.success("已標記完成。")
                st.session_state.pop("last_refresh", None)
                st.rerun()
    with col2:
        if st.button("任務失敗", disabled=is_done):
            if not player:
                st.error("找不到對應玩家。")
            else:
                logic.fail_task(task, player)
                st.warning("已標記失敗。")
                st.session_state.pop("last_refresh", None)
                st.rerun()
    with col3:
        if st.button("檢查逾時", disabled=is_done):
            logic.mark_overdue_tasks()
            st.info("已檢查逾時任務。")
            st.rerun()
