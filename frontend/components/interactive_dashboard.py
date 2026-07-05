from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import api


def format_money(value: float | int | None) -> str:
    return f"{float(value or 0):,.2f}"


def select_optional(label: str, options: list[Any], key: str) -> Any | None:
    if not options:
        return None
    choices = ["All", *options]
    selected = st.selectbox(label, choices, key=key)
    return None if selected == "All" else selected


def render_filters(options: dict[str, Any], dataset_id: int) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    with st.expander("Filters", expanded=True):
        date_range = options.get("date_range")
        row_one = st.columns(4)
        if date_range:
            start_default = date.fromisoformat(date_range["min"])
            end_default = date.fromisoformat(date_range["max"])
            filters["start_date"] = row_one[0].date_input("Start date", start_default, key=f"dash_start_{dataset_id}").isoformat()
            filters["end_date"] = row_one[1].date_input("End date", end_default, key=f"dash_end_{dataset_id}").isoformat()
            filters["year"] = select_optional("Year", options.get("years", []), f"dash_year_{dataset_id}")
            filters["month"] = select_optional("Month", options.get("months", []), f"dash_month_{dataset_id}")

        row_two = st.columns(5)
        filter_fields = [
            ("category", "Category"),
            ("subcategory", "Subcategory"),
            ("region", "Region"),
            ("state", "State"),
            ("customer_segment", "Segment"),
        ]
        for column, (role, label) in zip(row_two, filter_fields, strict=False):
            with column:
                filters[role] = select_optional(label, options.get(role, []), f"dash_{role}_{dataset_id}")
    return filters


def metric_cards(kpis: dict[str, Any]) -> None:
    cols = st.columns(5)
    cols[0].metric("Revenue", format_money(kpis.get("revenue")))
    cols[1].metric("Profit", format_money(kpis.get("profit")))
    cols[2].metric("Orders", f"{int(kpis.get('orders', 0)):,}")
    cols[3].metric("AOV", format_money(kpis.get("average_order_value")))
    cols[4].metric("Rows", f"{int(kpis.get('rows', 0)):,}")


def chart_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def render_bar(rows: list[dict], title: str, x: str, y: str) -> None:
    dataframe = chart_dataframe(rows)
    if dataframe.empty or x not in dataframe or y not in dataframe:
        st.caption(f"{title}: no matching data.")
        return
    st.plotly_chart(px.bar(dataframe, x=x, y=y, title=title), use_container_width=True)


def render_product_performance(rows: list[dict], product: str, metric: str) -> None:
    dataframe = chart_dataframe(rows)
    if dataframe.empty or product not in dataframe or metric not in dataframe:
        st.caption("Product performance: no matching data.")
        return

    top_products = dataframe.nlargest(10, metric).sort_values(metric)
    top_products["display_product"] = top_products[product].astype(str).str.wrap(32)
    figure = px.bar(
        top_products,
        x=metric,
        y="display_product",
        orientation="h",
        title="Product performance",
        custom_data=[product],
    )
    figure.update_traces(hovertemplate=f"%{{customdata[0]}}<br>{metric}: %{{x:,.2f}}<extra></extra>")
    figure.update_layout(
        height=max(420, len(top_products) * 42),
        margin={"l": 24, "r": 24, "t": 64, "b": 48},
        title_font={"size": 18},
        yaxis_title=None,
        xaxis_title_font={"size": 14},
    )
    st.plotly_chart(figure, use_container_width=True)


def render_interactive_dashboard(token: str) -> None:
    st.subheader("Interactive dashboard")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not datasets:
        st.caption("Upload a dataset to build an interactive dashboard.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
        key="interactive_dashboard_dataset",
    )

    try:
        seed_payload = api.get_interactive_dashboard(token, selected_id)
        filters = render_filters(seed_payload["filters"], selected_id)
        payload = api.get_interactive_dashboard(token, selected_id, filters)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    roles = payload["detected_roles"]
    metric = roles.get("revenue") or roles.get("profit") or roles.get("quantity")
    metric_label = metric or "value"

    metric_cards(payload["kpis"])

    trend = chart_dataframe(payload["trend"])
    if not trend.empty and metric_label in trend:
        st.plotly_chart(px.line(trend, x="date", y=metric_label, markers=True, title="Trend"), use_container_width=True)
    else:
        st.caption("Trend: no date-based metric available.")

    left, right = st.columns(2)
    with left:
        render_bar(payload["category_breakdown"], "Category performance", roles.get("category", "category"), metric_label)
        render_product_performance(payload["product_breakdown"], roles.get("product", "product"), metric_label)
    with right:
        render_bar(payload["region_breakdown"], "Regional performance", roles.get("region", "region"), metric_label)
        render_bar(
            payload["customer_segment_breakdown"],
            "Customer segment performance",
            roles.get("customer_segment", "customer_segment"),
            metric_label,
        )

    scatter = chart_dataframe(payload["scatter"])
    if not scatter.empty and roles.get("revenue") in scatter:
        x_axis = roles.get("profit") or roles.get("quantity")
        color = roles.get("category") if roles.get("category") in scatter else None
        st.plotly_chart(
            px.scatter(scatter, x=x_axis, y=roles["revenue"], color=color, hover_data=scatter.columns, title="Revenue drivers"),
            use_container_width=True,
        )

    treemap = chart_dataframe(payload["treemap"])
    if not treemap.empty and roles.get("category") in treemap and roles.get("product") in treemap and metric_label in treemap:
        st.plotly_chart(
            px.treemap(treemap, path=[roles["category"], roles["product"]], values=metric_label, title="Category and product mix"),
            use_container_width=True,
        )

    heatmap = chart_dataframe(payload["correlation_heatmap"])
    if not heatmap.empty:
        heatmap = heatmap.set_index("column")
        st.plotly_chart(px.imshow(heatmap, text_auto=True, title="Correlation heatmap"), use_container_width=True)
