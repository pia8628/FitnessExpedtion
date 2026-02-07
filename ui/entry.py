"""Game setup and entry page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui import get_logic_state, set_entered, render_header


def _validate_players(players: list[tuple[str, str]]) -> tuple[bool, str]:
    if not players:
        return False, "請至少新增 1 位玩家。"
    if len(players) > 5:
        return False, "玩家人數不可超過 5 位。"
    names = [name.strip() for name, _ in players]
    jobs = [job.strip() for _, job in players]
    if any(not n for n in names):
        return False, "玩家名稱不得為空。"
    if any(not j for j in jobs):
        return False, "職業不得為空。"
    if len(set(names)) != len(names):
        return False, "玩家名稱不可重複。"
    return True, ""


def render() -> None:
    render_header(page_title="進入遊戲", show_logo=False)
    home_image = Path(__file__).resolve().parent / "assets" / "home" / "home_image.png"
    if home_image.exists():
        st.image(str(home_image), width=900)
    try:
        logic = get_logic_state()
    except Exception as exc:
        st.error(f"無法連線到 Google Sheet：{exc}")
        st.caption("在此進入既有遊戲或建立新遊戲。")
        st.caption("建立新遊戲時請輸入玩家名稱與職業。")
        st.caption("完成後點選「進入遊戲」開始。")
        return

    job_options = logic.repo.get_job_options()
    job_label_map = {f"{code} {name}".strip(): code for code, name in job_options if code or name}
    tab_enter, tab_create = st.tabs(["進入既有遊戲", "建立新遊戲"])

    with tab_enter:
        st.subheader("進入既有遊戲")
        if not logic.players:
            st.info("尚無玩家資料，請先建立新遊戲。")
            return
        options = [p.name for p in logic.players]
        selected = st.selectbox("選擇玩家", options=options)
        if st.button("進入遊戲"):
            if not selected:
                st.warning("請先選擇玩家。")
            else:
                set_entered(True, active_player=selected)
                st.success(f"已以 {selected} 進入遊戲。")
                st.rerun()

    with tab_create:
        st.subheader("建立新遊戲")
        st.caption("建立新遊戲時，會初始化玩家狀態與技能。")
        player_count = st.slider("玩家人數", min_value=1, max_value=5, value=1)
        players: list[tuple[str, str]] = []
        for idx in range(player_count):
            col_name, col_job = st.columns(2)
            with col_name:
                name = st.text_input(f"玩家 {idx + 1} 名稱", key=f"new_player_name_{idx}")
            with col_job:
                if job_label_map:
                    label = st.selectbox(
                        f"玩家 {idx + 1} 職業",
                        options=list(job_label_map.keys()),
                        key=f"new_player_job_{idx}",
                    )
                    job = job_label_map[label]
                else:
                    job = st.text_input(f"玩家 {idx + 1} 職業", key=f"new_player_job_{idx}")
            players.append((name, job))

        confirm = st.checkbox("我已確認資料正確")
        if st.button("建立並進入遊戲", disabled=not confirm):
            ok, message = _validate_players(players)
            if not ok:
                st.warning(message)
            else:
                success, result = logic.create_new_game(players)
                if success:
                    set_entered(True, active_player=players[0][0])
                    st.success(result)
                    st.rerun()
                else:
                    st.error(result)

    st.caption("在此進入既有遊戲或建立新遊戲。")
    st.caption("建立新遊戲時請輸入玩家名稱與職業。")
    st.caption("完成後點選「進入遊戲」開始。")
