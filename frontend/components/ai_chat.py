from __future__ import annotations

import streamlit as st

from components.ai_typography import inject_ai_typography, render_ai_markdown, stable_ai_message_key
from utils import api


def render_ai_chat(token: str) -> None:
    inject_ai_typography()
    st.subheader("AI chat assistant")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not datasets:
        st.caption("Upload a dataset to chat with your business data.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
        key="ai_chat_dataset",
    )
    history_key = f"ai_chat_history_{selected_id}"
    st.session_state.setdefault(history_key, [])

    for index, message in enumerate(st.session_state[history_key]):
        with st.chat_message(message["role"]):
            render_ai_markdown(message["content"], key=stable_ai_message_key(message["content"], index))

    question = st.chat_input("Ask about this dataset")
    if not question:
        return

    st.session_state[history_key].append({"role": "user", "content": question})
    with st.chat_message("user"):
        render_ai_markdown(question, key=stable_ai_message_key(question, len(st.session_state[history_key]) - 1))

    try:
        with st.spinner("Thinking with dataset context..."):
            response = api.ask_dataset_question(token, selected_id, question)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    answer = response["answer"]
    st.session_state[history_key].append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        render_ai_markdown(answer, key=stable_ai_message_key(answer, len(st.session_state[history_key]) - 1))
