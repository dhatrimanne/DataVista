import streamlit as st
import plotly.graph_objects as go


def render_metric_grid(summary: dict) -> None:
    first_row = st.columns(4)
    first_row[0].metric("Datasets", summary["total_datasets"])
    first_row[1].metric("Reports", summary["total_reports"])
    first_row[2].metric("AI insights", summary["ai_insights_generated"])
    first_row[3].metric("Forecasts", summary["forecasts_generated"])

    score = summary["business_health_score"]
    score_label = "Not enough data" if score is None else f"{score}/100"
    second_row = st.columns([1, 3])
    second_row[0].metric("Business health", score_label)
    second_row[1].info(summary["business_health_status"])

    if score is not None:
        gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#2563eb"},
                    "steps": [
                        {"range": [0, 55], "color": "#fee2e2"},
                        {"range": [55, 75], "color": "#fef3c7"},
                        {"range": [75, 100], "color": "#dcfce7"},
                    ],
                },
            )
        )
        gauge.update_layout(height=260, margin={"l": 20, "r": 20, "t": 20, "b": 10})
        st.plotly_chart(gauge, use_container_width=True)
        factors = summary.get("business_health_factors", [])
        if factors:
            st.dataframe(factors, hide_index=True, use_container_width=True)


def render_recent_activity(summary: dict) -> None:
    st.subheader("Recent activity")
    activity = summary["recent_activity"]
    if not activity:
        st.caption("No workspace activity yet.")
        return

    for event in activity:
        st.write(f"**{event['message']}**")
        st.caption(f"{event['event_type']} - {event['created_at']}")


def render_profile(user: dict, summary: dict) -> None:
    st.subheader("Profile")
    profile = {
        "Name": user["full_name"],
        "Email": user["email"],
        "Created": user["created_at"],
        "Last login": summary["last_login_at"] or "First session",
    }
    rows = [{"Field": key, "Value": value} for key, value in profile.items()]
    st.dataframe(rows, hide_index=True, use_container_width=True)
