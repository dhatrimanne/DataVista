import pandas as pd
import plotly.express as px
import streamlit as st

from utils import api


def render_kpis(kpis: dict) -> None:
    if not kpis:
        return
    columns = st.columns(len(kpis))
    labels = {
        "revenue": "Revenue",
        "profit": "Profit",
        "orders": "Orders",
        "average_order_value": "Average order value",
    }
    for column, (key, value) in zip(columns, kpis.items(), strict=False):
        formatted = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
        column.metric(labels.get(key, key.replace("_", " ").title()), formatted)


def render_time_analysis(analysis: dict, metric: str) -> None:
    time_analysis = analysis.get("time_analysis", {})
    if not time_analysis:
        return
    st.subheader("Time analysis")
    grain = st.segmented_control(
        "Period",
        options=list(time_analysis.keys()),
        default="monthly" if "monthly" in time_analysis else next(iter(time_analysis)),
        key="eda_time_grain",
    )
    rows = time_analysis.get(grain, [])
    if rows:
        frame = pd.DataFrame(rows)
        x_column = next(column for column in frame.columns if column != metric)
        st.plotly_chart(px.line(frame, x=x_column, y=metric, markers=True), use_container_width=True)


def render_rankings(title: str, rankings: dict, dimension: str, metric: str) -> None:
    if not rankings:
        return
    st.subheader(title)
    tabs = st.tabs([key.replace("_", " ").title() for key in rankings])
    for tab, (_, rows) in zip(tabs, rankings.items(), strict=False):
        with tab:
            if rows:
                frame = pd.DataFrame(rows)
                y_column = metric if metric in frame.columns else frame.columns[-1]
                st.plotly_chart(
                    px.bar(frame, x=dimension, y=y_column, color=y_column),
                    use_container_width=True,
                )


def render_customer_analysis(customer_analysis: dict, customer_column: str | None) -> None:
    if not customer_analysis or not customer_column:
        return
    st.subheader("Customer analysis")
    cols = st.columns(2)
    cols[0].metric("Repeat customers", customer_analysis.get("repeat_customers", 0))
    cols[1].metric("Average lifetime value", f"{customer_analysis.get('customer_lifetime_value_average', 0):,.2f}")
    top_customers = customer_analysis.get("top_customers", [])
    if top_customers:
        frame = pd.DataFrame(top_customers)
        st.plotly_chart(px.bar(frame, x=customer_column, y="revenue", color="value_segment"), use_container_width=True)
    if customer_analysis.get("rfm"):
        st.write("RFM analysis")
        st.dataframe(customer_analysis["rfm"], hide_index=True, use_container_width=True)


def render_statistics(statistics: dict) -> None:
    correlation = statistics.get("correlation", [])
    distributions = statistics.get("distributions", [])
    if not correlation and not distributions:
        return
    st.subheader("Statistical analysis")
    if distributions:
        st.dataframe(distributions, hide_index=True, use_container_width=True)
    if correlation:
        frame = pd.DataFrame(correlation).set_index("column")
        st.plotly_chart(
            px.imshow(frame.astype(float), text_auto=True, aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1),
            use_container_width=True,
        )


def render_analysis(token: str) -> None:
    st.subheader("Exploratory analysis")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return
    if not datasets:
        st.caption("Upload a dataset to generate analysis.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
    )
    if st.button("Regenerate analysis", use_container_width=False):
        try:
            api.regenerate_dataset_analysis(token, selected_id)
            st.success("Analysis regenerated.")
        except api.ApiError as exc:
            st.error(str(exc))

    try:
        analysis = api.get_dataset_analysis(token, selected_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    roles = analysis["detected_roles"]
    render_kpis(analysis["kpis"])
    primary_metric = roles.get("revenue") or roles.get("profit")
    if primary_metric:
        render_time_analysis(analysis, primary_metric)
    render_customer_analysis(analysis["customer_analysis"], roles.get("customer"))
    if roles.get("product") and primary_metric:
        render_rankings("Product analysis", analysis["product_analysis"], roles["product"], primary_metric)
    if roles.get("region") and primary_metric:
        render_rankings("Regional analysis", analysis["regional_analysis"], roles["region"], primary_metric)
    render_statistics(analysis["statistical_analysis"])

    if analysis["unavailable_sections"]:
        st.info("Unavailable for this dataset: " + ", ".join(analysis["unavailable_sections"]))
