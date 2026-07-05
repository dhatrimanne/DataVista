import streamlit as st

from utils import api


def persist_auth(auth_response: dict) -> None:
    st.session_state["access_token"] = auth_response["access_token"]
    st.session_state["user"] = auth_response["user"]


def render_login() -> None:
    with st.form("login_form"):
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        remember_me = st.checkbox("Remember me", value=True)
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        try:
            persist_auth(api.login(email, password, remember_me))
            st.rerun()
        except api.ApiError as exc:
            st.error(str(exc))


def render_registration() -> None:
    with st.form("registration_form"):
        full_name = st.text_input("Full name", autocomplete="name")
        email = st.text_input("Work email", autocomplete="email")
        password = st.text_input("Password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Create account", use_container_width=True)

    if submitted:
        try:
            persist_auth(api.register(email, full_name, password))
            st.rerun()
        except api.ApiError as exc:
            st.error(str(exc))


def render_logout() -> None:
    if st.sidebar.button("Log out", use_container_width=True):
        token = st.session_state.get("access_token")
        if token:
            try:
                api.logout(token)
            except api.ApiError:
                pass
        st.session_state.clear()
        st.rerun()
