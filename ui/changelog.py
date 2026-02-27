"""Changelog page."""

import streamlit as st

from ui import render_header


def render() -> None:
    render_header(page_title="版本更新")

    entries = [
        {
            "version": "0.1.3beta",
            "date": "2026-02-27",
            "notes": [
                "修正升級時 HP 和 MP 計算錯誤的問題。",
                "修正角色死亡、復活後，HP 沒有恢復的問題。",
                "新增任務擊殺模式，區分為完美擊殺與一般擊殺。",
                "個人額外抽卡，抽卡頁可用下拉式選單指定怪物。",
            ],
        },
        {
            "version": "0.1.2 beta",
            "date": "2026-02-17",
            "notes": [
                "視覺更新：古典卷軸主題、溫暖金色邊框與層次背景。",
                "地圖卡片：狀態總覽新增地圖卡片，支援竹林、森林、陰影山丘。",
                "任務體驗：可直接確認所有怪物任務清單，維持正常顯示。",
                "資料精簡：表格僅顯示玩家必要欄位。",
                "週結算文案：將「下兩週」改為「未來」。",
                "狀態顯示：任務狀態改為「擊殺 / 失敗」，不再出現亂碼。",
            ],
        },
        {
            "version": "0.1.1 beta",
            "date": "2026-02-07",
            "notes": [
                "新增遊戲 LOGO 與頁面說明文字。",
                "新增版本更新頁面與獨立顯示。",
                "修正已知 Bug。",
            ],
        },
        {
            "version": "0.1.0",
            "date": "2026-01-30",
            "notes": [
                "遊戲初版推出。",
            ],
        },
    ]

    for entry in entries:
        st.subheader(f"{entry['version']} ({entry['date']})")
        for note in entry["notes"]:
            st.write(f"- {note}")
