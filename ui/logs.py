"""Logs page."""

import streamlit as st

from ui import get_logic_state, render_header


def render() -> None:
    render_header(page_title="紀錄")
    try:
        logic = get_logic_state()
        header, data = logic.repo.get_logs(limit=200)
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        return

    home_week, _ = logic.repo.get_home_status()
    if home_week and home_week > 0:
        st.caption(f"遊玩總回合數：{home_week}")

    if not header:
        st.info("尚無紀錄資料。")
        return

    rows = []
    for row in data:
        padded = row + [""] * (len(header) - len(row))
        rows.append(dict(zip(header, padded)))

    players = sorted({r.get("玩家", "") for r in rows if r.get("玩家")})
    types = sorted({r.get("類型", "") for r in rows if r.get("類型")})

    player_filter = st.selectbox("玩家", options=["全部"] + players)
    type_filter = st.selectbox("類型", options=["全部"] + types)

    if player_filter != "全部":
        rows = [r for r in rows if r.get("玩家") == player_filter]
    if type_filter != "全部":
        rows = [r for r in rows if r.get("類型") == type_filter]

    if rows:
        def week_key(value: str):
            text = str(value).strip()
            if not text:
                return -1
            try:
                return int(float(text))
            except Exception:
                return -1

        def date_key(value: str):
            return str(value).strip()

        groups = {}
        for item in rows:
            week_value = item.get("週數", "")
            groups.setdefault(week_value, []).append(item)

        weeks_sorted = sorted(groups.keys(), key=week_key, reverse=True)
        for week_value in weeks_sorted:
            label = str(week_value).strip() or "未標記回合"
            st.subheader(f"回合：{label}")
            group_rows = sorted(
                groups[week_value], key=lambda r: date_key(r.get("日期", "")), reverse=True
            )
            view_rows = []
            for r in group_rows:
                view_rows.append(
                    {
                        "日期": r.get("日期", ""),
                        "回合": r.get("週數", ""),
                        "玩家": r.get("玩家", ""),
                        "類型": r.get("類型", ""),
                        "名稱": r.get("名稱", ""),
                        "效果說明": r.get("效果說明", ""),
                    }
                )
            st.table(view_rows)
    else:
        st.info("沒有符合條件的紀錄。")

    st.caption("查看任務、技能、事件等紀錄。")
    st.caption("可用篩選器鎖定玩家或類型。")

