"""Dashboard page."""

import streamlit as st

from ui import get_logic_state


def _build_skill_summary(player_name: str, skill_states) -> str:
    parts = []
    for state in skill_states:
        if state.player != player_name:
            continue
        if not state.enabled or state.enabled.upper() != "Y":
            continue
        name = state.name or state.skill_id
        remaining = state.remaining
        remaining_text = "∞" if remaining is None else str(remaining)
        parts.append(f"{name}({remaining_text})")
    return "、".join(parts)


def render() -> None:
    st.header("狀態總覽")
    try:
        logic = get_logic_state()
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        return

    st.subheader("玩家狀態")
    job_map = {code: name for code, name in logic.repo.get_job_options()}
    skill_states = logic.repo.get_skill_states()
    players = []
    for p in logic.players:
        players.append(
            {
                "玩家": p.name,
                "職業": job_map.get(p.job, p.job),
                "等級": p.level,
                "EXP": p.exp,
                "HP": f"{p.hp_current}/{p.hp_max}",
                "MP": f"{p.mp_current}/{p.mp_max}",
                "技能摘要": _build_skill_summary(p.name, skill_states),
                "懲罰剩餘週數": p.penalty_weeks,
            }
        )
    if players:
        st.table(players)
    else:
        st.info("尚無玩家資料。")

    st.subheader("任務狀態")
    tasks = []
    for t in logic.tasks:
        tasks.append(
            {
                "怪物ID": t.monster_id,
                "玩家": t.player,
                "怪物名稱": t.name,
                "難度": t.difficulty,
                "任務內容": t.content,
                "截止日": t.deadline or "",
                "狀態": t.status,
                "成功EXP": t.success_exp,
                "失敗-HP": t.fail_hp,
            }
        )
    if tasks:
        st.table(tasks)
    else:
        st.info("尚無任務資料。")

    st.subheader("本週事件")
    home_week, home_map_id = logic.repo.get_home_status()
    display_week = home_week if home_week and home_week > 0 else None
    event = None
    if display_week:
        event = logic.get_event_for_week(display_week)
    if event:
        st.write(
            {
                "回合": display_week,
                "事件代碼": event.event_id,
                "事件名稱": event.name,
                "事件效果": f"{event.effect_code} {event.description}".strip(),
            }
        )
    else:
        try:
            header, data = logic.repo.get_logs(limit=200)
        except Exception:
            header, data = [], []
        if header and data:
            type_idx = header.index("類型") if "類型" in header else None
            code_idx = header.index("代碼") if "代碼" in header else None
            name_idx = header.index("名稱") if "名稱" in header else None
            desc_idx = header.index("效果說明") if "效果說明" in header else None
            last_event = None
            for row in reversed(data):
                if type_idx is None or len(row) <= type_idx:
                    continue
                if row[type_idx] != "抽事件":
                    continue
                last_event = row
                break
            if last_event:
                st.write(
                    {
                        "事件代碼": last_event[code_idx]
                        if code_idx is not None and len(last_event) > code_idx
                        else "",
                        "事件名稱": last_event[name_idx]
                        if name_idx is not None and len(last_event) > name_idx
                        else "",
                        "事件效果": last_event[desc_idx]
                        if desc_idx is not None and len(last_event) > desc_idx
                        else "",
                    }
                )
            else:
                st.info("尚無事件紀錄。")
        else:
            st.info("尚無事件紀錄。")

    st.subheader("目前地圖")
    maps = logic.repo.get_maps()
    if maps:
        current_map = None
        if home_map_id:
            current_map = next((m for m in maps if m.map_id == home_map_id), None)
        if current_map is None and display_week:
            current_map = next((m for m in maps if m.week == display_week), None)
        if current_map is None:
            current_map = max(maps, key=lambda m: m.week)
        boss_stage = logic.is_boss_stage(current_map)
        boss_settled = (
            logic.has_boss_settlement_for_week(display_week)
            if display_week
            else False
        )
        st.write(
            {
                "回合": display_week if display_week else current_map.week,
                "地圖名稱": current_map.name,
                "地圖難度": current_map.difficulty_count,
                "Easy機率": current_map.easy_rate,
                "Medium機率": current_map.medium_rate,
                "Hard機率": current_map.hard_rate,
                "BOSS編號": current_map.boss_id,
                "BOSS階段": "是" if boss_stage else "否",
                "BOSS結算": "已完成" if boss_settled else "未完成",
            }
        )
    else:
        st.info("地圖表無資料。")
