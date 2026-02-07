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


def render_header(page_title: str | None = None, show_logo: bool = True, logo_width: int = 140) -> None:
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
