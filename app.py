"""
Streamlit entrypoint.

Wires UI pages and connects to domain logic. Requires .env with SHEET_ID,
TIMEZONE, and Google service account credentials.
"""

import streamlit as st

# Lazy imports to avoid circular refs during early development.
from ui import dashboard, tasks, skills_view, logs, draws, entry, is_entered, get_active_player, set_entered


def main() -> None:
    st.set_page_config(page_title="Fitness Expedtion", layout="wide")
    st.markdown("<div style='text-align: right; font-size: 12px; color: #666;'>v0.5</div>", unsafe_allow_html=True)
    if not is_entered():
        st.sidebar.radio("頁面", options=["進入遊戲"], index=0)
        entry.render()
        return

    active_player = get_active_player()
    if active_player:
        st.sidebar.caption(f"目前玩家：{active_player}")
    if st.sidebar.button("離開遊戲"):
        set_entered(False)
        st.rerun()

    page = st.sidebar.radio(
        "頁面",
        options=["狀態總覽", "週結算", "任務", "技能", "紀錄"],
    )

    if page == "狀態總覽":
        dashboard.render()
    elif page == "週結算":
        draws.render()
    elif page == "任務":
        tasks.render()
    elif page == "技能":
        skills_view.render()
    elif page == "紀錄":
        logs.render()


if __name__ == "__main__":
    main()
