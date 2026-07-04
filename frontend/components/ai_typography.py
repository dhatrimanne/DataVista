from __future__ import annotations

import hashlib
import re

import streamlit as st


AI_TYPOGRAPHY_CSS = """
<style>
.st-key-ai_insights_copy div[data-testid="stMarkdown"],
.st-key-ai_chat_copy div[data-testid="stMarkdown"],
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    color: #0f172a;
}

.st-key-ai_insights_copy div[data-testid="stMarkdown"] p,
.st-key-ai_insights_copy div[data-testid="stMarkdown"] li,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] p,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] li,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] p,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] li {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    font-size: 0.98rem;
    line-height: 1.7;
    letter-spacing: 0;
    white-space: normal;
    word-break: normal;
    overflow-wrap: normal;
    margin-bottom: 0.85rem;
}

.st-key-ai_insights_copy div[data-testid="stMarkdown"] h1,
.st-key-ai_insights_copy div[data-testid="stMarkdown"] h2,
.st-key-ai_insights_copy div[data-testid="stMarkdown"] h3,
.st-key-ai_insights_copy div[data-testid="stMarkdown"] h4,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] h1,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] h2,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] h3,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] h4,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] h1,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] h2,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] h3,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] h4 {
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    letter-spacing: 0;
    line-height: 1.28;
    margin-top: 1.2rem;
    margin-bottom: 0.55rem;
}

.st-key-ai_insights_copy div[data-testid="stMarkdown"] ul,
.st-key-ai_insights_copy div[data-testid="stMarkdown"] ol,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] ul,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] ol,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] ul,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] ol {
    margin-top: 0.35rem;
    margin-bottom: 1rem;
    padding-left: 1.35rem;
}

.st-key-ai_insights_copy div[data-testid="stMarkdown"] strong,
.st-key-ai_chat_copy div[data-testid="stMarkdown"] strong,
div[class*="st-key-ai_chat_message_"] div[data-testid="stMarkdown"] strong {
    font-weight: 650;
}
</style>
"""


def preserve_currency_markdown(content: str) -> str:
    return re.sub(r"(?<!\\)\$", r"\\$", content)


def inject_ai_typography() -> None:
    if st.session_state.get("_ai_typography_css_loaded"):
        return
    st.markdown(AI_TYPOGRAPHY_CSS, unsafe_allow_html=True)
    st.session_state["_ai_typography_css_loaded"] = True


def render_ai_markdown(content: str, key: str) -> None:
    inject_ai_typography()
    with st.container(key=key):
        st.markdown(preserve_currency_markdown(content))


def stable_ai_message_key(content: str, index: int) -> str:
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"ai_chat_message_{index}_{digest}"
