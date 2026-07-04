import streamlit as st

from frontend.components.auth import render_login, render_logout, render_registration
from frontend.components.ai_chat import render_ai_chat
from frontend.components.ai_insights import render_ai_insights
from frontend.components.analysis import render_analysis
from frontend.components.dashboard import render_metric_grid, render_profile, render_recent_activity
from frontend.components.datasets import render_dataset_manager
from frontend.components.interactive_dashboard import render_interactive_dashboard
from frontend.components.machine_learning import render_machine_learning
from frontend.components.notifications import render_notifications
from frontend.components.recommendations import render_recommendations
from frontend.components.reports import render_report_center
from frontend.components.settings import render_settings
from frontend.utils import api


st.set_page_config(page_title="DataVista", page_icon=":bar_chart:", layout="wide")


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 96px;
        }
        div[data-testid="stMetricLabel"] p {
            color: #475569;
            font-size: 0.9rem;
            font-weight: 600;
        }
        div[data-testid="stMetricValue"] {
            color: #0f172a;
            font-weight: 700;
        }
        .stDataFrame {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def restore_user() -> None:
    token = st.session_state.get("access_token")
    if not token or st.session_state.get("user"):
        return
    try:
        st.session_state["user"] = api.fetch_profile(token)
    except api.ApiError:
        st.session_state.clear()


def render_auth_screen() -> None:
    st.title("DataVista")
    st.caption("AI-powered business analytics for private, user-scoped workspaces.")

    login_tab, register_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        render_login()
    with register_tab:
        render_registration()


def render_dashboard_shell() -> None:
    user = st.session_state["user"]
    token = st.session_state["access_token"]
    st.sidebar.title("DataVista")
    st.sidebar.caption(user["email"])
    render_logout()

    st.title("Dashboard")
    st.caption("Your private DataVista workspace.")

    try:
        summary = api.fetch_dashboard_summary(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    dashboard_tab, datasets_tab, interactive_tab, analysis_tab, ml_tab, insights_tab, chat_tab, recommendations_tab, reports_tab, notifications_tab, settings_tab = st.tabs(
        ["Overview", "Datasets", "Interactive", "Analysis", "ML", "AI Insights", "AI Chat", "Recommendations", "Reports", "Notifications", "Settings"]
    )
    with dashboard_tab:
        render_metric_grid(summary)
        left, right = st.columns([2, 1])
        with left:
            render_recent_activity(summary)
        with right:
            render_profile(user, summary)
    with datasets_tab:
        render_dataset_manager(token)
    with interactive_tab:
        render_interactive_dashboard(token)
    with analysis_tab:
        render_analysis(token)
    with ml_tab:
        render_machine_learning(token)
    with insights_tab:
        render_ai_insights(token)
    with chat_tab:
        render_ai_chat(token)
    with recommendations_tab:
        render_recommendations(token)
    with reports_tab:
        render_report_center(token)
    with notifications_tab:
        render_notifications(token)
    with settings_tab:
        render_settings(token)


apply_global_styles()
restore_user()
if "user" in st.session_state:
    render_dashboard_shell()
else:
    render_auth_screen()
