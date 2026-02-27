"""Shared UI helpers."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from data.repositories import Repositories
from data.sheets_client import SheetsClient
from domain.logic import Logic
from config.settings import APP_VERSION


def get_logic() -> Logic:
    if "logic" not in st.session_state:
        client = SheetsClient()
        repo = Repositories(client)
        st.session_state["logic"] = Logic(repo)
    return st.session_state["logic"]


def get_logic_state() -> Logic:
    logic = get_logic()
    if "last_refresh" not in st.session_state:
        logic.refresh_state()
        st.session_state["last_refresh"] = True
    _consume_pending_notifications(logic)
    return logic


def is_entered() -> bool:
    return bool(st.session_state.get("entered"))


def set_entered(value: bool, active_player: str | None = None) -> None:
    st.session_state["entered"] = value
    if active_player:
        st.session_state["active_player"] = active_player
    elif "active_player" in st.session_state:
        st.session_state.pop("active_player")


def get_active_player() -> str | None:
    return st.session_state.get("active_player")


def _consume_pending_notifications(logic: Logic) -> None:
    queue = st.session_state.setdefault("notification_queue", [])
    queue.extend(logic.pop_pending_notifications())


def render_notification_modal() -> None:
    queue = st.session_state.get("notification_queue", [])
    if not queue:
        return
    current = queue[0]
    title = current.get("title", "提示")
    message = current.get("message", "")
    skills = current.get("skills", [])
    no_skill_message = current.get("no_skill_message", "")

    def _confirm() -> None:
        queue = st.session_state.get("notification_queue", [])
        if queue:
            queue.pop(0)
        st.session_state["notification_queue"] = queue

    if hasattr(st, "dialog"):
        @st.dialog(title)
        def _dialog():
            if message:
                st.write(message)
            for item in skills:
                st.write(f"- {item.get('name', '')}：{item.get('description', '')}")
            if (not skills) and no_skill_message:
                st.write(no_skill_message)
            if st.button("確定", key="notification_confirm_dialog"):
                _confirm()
                st.rerun()

        _dialog()
        return

    # Fallback for older Streamlit without st.dialog.
    with st.container(border=True):
        st.subheader(title)
        if message:
            st.write(message)
        for item in skills:
            st.write(f"- {item.get('name', '')}：{item.get('description', '')}")
        if (not skills) and no_skill_message:
            st.write(no_skill_message)
        if st.button("確定", key="notification_confirm_fallback"):
            _confirm()
            st.rerun()


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Noto+Sans+TC:wght@400;500;600&display=swap');

        :root {
          --journal-bg: #f8f3ee;
          --journal-surface: #fff8f2;
          --journal-ink: #3c2f2a;
          --journal-muted: #7a6f68;
          --journal-line: #e7dcd3;
          --accent-orange: #ff8a3d;
          --accent-coral: #ff5d73;
          --accent-rose: #f3b4a4;
        }

        .stApp {
          background: radial-gradient(1200px 500px at 10% -10%, #fde9e1 0%, rgba(253,233,225,0) 60%),
                      radial-gradient(900px 400px at 90% -10%, #fff1dd 0%, rgba(255,241,221,0) 55%),
                      var(--journal-bg);
          color: var(--journal-ink);
          font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
        }

        h1, h2, h3, h4 {
          font-family: "Playfair Display", "Noto Serif TC", serif;
          letter-spacing: 0.2px;
        }

        .block-container {
          padding-top: 2.2rem;
          padding-bottom: 3rem;
        }

        .journal-card {
          background: var(--journal-surface);
          border: 1px solid var(--journal-line);
          border-radius: 16px;
          padding: 14px 16px;
          box-shadow: 0 8px 20px rgba(44, 32, 24, 0.06);
        }

        .stButton>button {
          background: var(--accent-orange);
          color: #fff;
          border: none;
          border-radius: 12px;
          padding: 0.45rem 0.9rem;
          font-weight: 600;
        }
        .stButton>button:hover {
          background: var(--accent-coral);
        }

        .stTable, .stDataFrame {
          background: var(--journal-surface);
          border-radius: 12px;
          border: 1px solid var(--journal-line);
        }
        .stTable table, .stDataFrame table {
          border-collapse: separate;
          border-spacing: 0;
        }
        .stTable th, .stDataFrame th {
          background: #f6eae1;
          color: var(--journal-ink);
        }
        .stTable td, .stDataFrame td {
          color: var(--journal-ink);
          padding: 0.5rem 0.7rem;
        }
        .stTable tr:nth-child(even) td, .stDataFrame tr:nth-child(even) td {
          background: #fff3ea;
        }

        .stImage img {
          border-radius: 16px;
          border: 1px solid var(--journal-line);
          box-shadow: 0 8px 20px rgba(44, 32, 24, 0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(page_title: str | None = None, show_logo: bool = True, logo_width: int = 140) -> None:
    _apply_theme()
    logo_path = Path(__file__).resolve().parent / "assets" / "branding" / "logo.png"
    if show_logo and logo_path.exists():
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            st.image(str(logo_path), width=logo_width)
        with col_title:
            if page_title:
                st.markdown(f"## {page_title}")
    else:
        if page_title:
            st.header(page_title)
    st.markdown(
        f"<div style='text-align: right; font-size: 12px; color: #666;'>版本 {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
