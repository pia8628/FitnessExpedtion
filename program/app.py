"""
Streamlit entrypoint.

Wires UI pages and connects to domain logic. Requires .env with SHEET_ID,
TIMEZONE, and Google service account credentials.
"""

import streamlit as st

# Lazy imports to avoid circular refs during early development.
from ui import dashboard, tasks, skills_view, logs, draws


def main() -> None:
    st.set_page_config(page_title="Fitness Expedtion", layout="wide")
    page = st.sidebar.radio(
        "頁面",
        options=["Dashboard", "週結算", "任務", "技能", "紀錄"],
    )

    if page == "Dashboard":
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
