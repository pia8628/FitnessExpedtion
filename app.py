"""
Streamlit entrypoint.

Wires UI pages and connects to domain logic. Requires .env with SHEET_ID,
TIMEZONE, and Google service account credentials.
"""

import streamlit as st

# Lazy imports to avoid circular refs during early development.
from ui import (
    dashboard,
    tasks,
    skills_view,
    logs,
    draws,
    entry,
    changelog,
    is_entered,
    get_active_player,
    set_entered,
    render_notification_modal,
)

def main() -> None:
    st.set_page_config(page_title="活力遠征 Fitness Expedition", layout="wide")
    if not is_entered():
        st.sidebar.radio("頁面", options=["進入遊戲"], index=0)
        entry.render()
        return

    active_player = get_active_player()
    if active_player:
        st.sidebar.caption(f"目前玩家：{active_player}")
    if st.sidebar.button("返回進入遊戲"):
        set_entered(False)
        st.rerun()

    page = st.sidebar.radio(
        "頁面",
        options=["狀態總覽", "回合與抽卡", "任務", "技能", "紀錄", "版本更新"],
    )

    if page == "狀態總覽":
        dashboard.render()
    elif page == "回合與抽卡":
        draws.render()
    elif page == "任務":
        tasks.render()
    elif page == "技能":
        skills_view.render()
    elif page == "紀錄":
        logs.render()
    elif page == "版本更新":
        changelog.render()

    render_notification_modal()

if __name__ == "__main__":
    main()
