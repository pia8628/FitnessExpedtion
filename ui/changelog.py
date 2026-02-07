"""Changelog page."""

import streamlit as st

from ui import render_header


def render() -> None:
    render_header(page_title="版本更新")

    entries = [
        {
            "version": "0.1.1 beta",
            "date": "2026-02-07",
            "notes": [
                "新增遊戲LOGO與頁面說明文字。",
                "新增版本更新頁面與版本號顯示。",
                "修改已知Bug。",
            ],
        },
        {
            "version": "0.1.0",
            "date": "2026-01-30",
            "notes": [
                "初版釋出。",
            ],
        },
    ]

    for entry in entries:
        st.subheader(f"{entry['version']} ({entry['date']})")
        for note in entry["notes"]:
            st.write(f"• {note}")


