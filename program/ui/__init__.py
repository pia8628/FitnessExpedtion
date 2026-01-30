"""Shared UI helpers."""

from __future__ import annotations

import streamlit as st

from data.repositories import Repositories
from data.sheets_client import SheetsClient
from domain.logic import Logic


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
