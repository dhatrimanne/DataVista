from __future__ import annotations

import streamlit as st

from utils import api


def render_settings(token: str) -> None:
    st.subheader("Settings")
    user = st.session_state["user"]

    st.write("Profile")
    full_name = st.text_input("Full name", value=user["full_name"])
    if st.button("Save profile"):
        try:
            st.session_state["user"] = api.update_profile(token, full_name)
            st.success("Profile updated.")
            st.rerun()
        except api.ApiError as exc:
            st.error(str(exc))

    st.write("Password")
    current_password = st.text_input("Current password", type="password")
    new_password = st.text_input("New password", type="password")
    if st.button("Change password"):
        try:
            api.change_password(token, current_password, new_password)
            st.success("Password changed.")
        except api.ApiError as exc:
            st.error(str(exc))

    st.write("Preferences")
    theme = st.segmented_control(
        "Theme",
        ["system", "light", "dark"],
        default=user.get("theme", "system"),
    )
    model = st.text_input("Gemini model", value=user.get("preferred_gemini_model") or "gemini-2.5-flash")
    if st.button("Save preferences"):
        try:
            st.session_state["user"] = api.update_preferences(token, theme, model)
            st.success("Preferences updated.")
            st.rerun()
        except api.ApiError as exc:
            st.error(str(exc))

    st.write("Account")
    confirm = st.checkbox("I understand this disables my account")
    if st.button("Delete account", disabled=not confirm):
        try:
            api.delete_account(token)
            st.session_state.clear()
            st.success("Account deleted.")
            st.rerun()
        except api.ApiError as exc:
            st.error(str(exc))
