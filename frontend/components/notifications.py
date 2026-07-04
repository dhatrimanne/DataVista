from __future__ import annotations

import streamlit as st

from frontend.utils import api


def render_notifications(token: str) -> None:
    st.subheader("Notification center")
    try:
        notifications = api.list_notifications(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not notifications:
        st.caption("No notifications yet.")
        return

    for notification in notifications:
        st.write(f"**{notification['message']}**")
        st.caption(f"{notification['event_type']} - {notification['created_at']}")
