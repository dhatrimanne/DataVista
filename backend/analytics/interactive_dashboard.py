from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

from backend.analytics.eda import detect_roles, json_value, records


FILTER_ROLES = ("category", "subcategory", "region", "state", "customer_segment")
FILTER_ALIASES = {
    "subcategory": ("subcategory", "sub_category", "product_subcategory"),
    "state": ("state", "province"),
    "customer_segment": ("segment", "customer_segment", "customer_type"),
}


@dataclass(frozen=True)
class DashboardFilters:
    start_date: str | None = None
    end_date: str | None = None
    year: int | None = None
    month: int | None = None
    category: str | None = None
    subcategory: str | None = None
    region: str | None = None
    state: str | None = None
    customer_segment: str | None = None


def detect_dashboard_roles(dataframe: pd.DataFrame) -> dict[str, str]:
    roles = detect_roles(dataframe)
    columns = list(dataframe.columns)
    for role, aliases in FILTER_ALIASES.items():
        exact = next((column for column in columns if column in aliases), None)
        if exact:
            roles[role] = exact
            continue
        partial = next((column for column in columns if any(alias in column for alias in aliases)), None)
        if partial:
            roles[role] = partial
    return roles


def safe_total(dataframe: pd.DataFrame, column: str | None) -> float:
    if not column or column not in dataframe:
        return 0.0
    return float(pd.to_numeric(dataframe[column], errors="coerce").fillna(0).sum())


def unique_options(series: pd.Series, limit: int = 200) -> list[Any]:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""].drop_duplicates().sort_values().head(limit)
    return [json_value(value) for value in values.tolist()]


def apply_filters(dataframe: pd.DataFrame, roles: dict[str, str], filters: DashboardFilters) -> pd.DataFrame:
    filtered = dataframe.copy()
    date_column = roles.get("date")
    if date_column:
        dates = pd.to_datetime(filtered[date_column], errors="coerce")
        filtered = filtered.assign(_dashboard_date=dates)
        if filters.start_date:
            filtered = filtered[filtered["_dashboard_date"] >= pd.to_datetime(filters.start_date, errors="coerce")]
        if filters.end_date:
            filtered = filtered[filtered["_dashboard_date"] <= pd.to_datetime(filters.end_date, errors="coerce")]
        if filters.year:
            filtered = filtered[filtered["_dashboard_date"].dt.year == filters.year]
        if filters.month:
            filtered = filtered[filtered["_dashboard_date"].dt.month == filters.month]

    for role in FILTER_ROLES:
        value = getattr(filters, role)
        column = roles.get(role)
        if value and column:
            filtered = filtered[filtered[column].astype(str) == str(value)]

    return filtered.drop(columns=["_dashboard_date"], errors="ignore")


def build_filter_options(dataframe: pd.DataFrame, roles: dict[str, str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    date_column = roles.get("date")
    if date_column:
        dates = pd.to_datetime(dataframe[date_column], errors="coerce").dropna()
        if not dates.empty:
            options["date_range"] = {
                "min": dates.min().date().isoformat(),
                "max": dates.max().date().isoformat(),
            }
            options["years"] = sorted(int(year) for year in dates.dt.year.dropna().unique())
            options["months"] = sorted(int(month) for month in dates.dt.month.dropna().unique())

    for role in FILTER_ROLES:
        column = roles.get(role)
        if column:
            options[role] = unique_options(dataframe[column])
    return options


def aggregate_dimension(dataframe: pd.DataFrame, dimension: str | None, metric: str | None, limit: int = 12) -> list[dict]:
    if not dimension or not metric or dataframe.empty:
        return []
    grouped = dataframe.groupby(dimension, dropna=False)[metric].sum().sort_values(ascending=False).reset_index()
    return records(grouped, limit=limit)


def build_trend(dataframe: pd.DataFrame, date_column: str | None, metric: str | None) -> list[dict]:
    if not date_column or not metric or dataframe.empty:
        return []
    dates = pd.to_datetime(dataframe[date_column], errors="coerce")
    valid = dataframe.loc[dates.notna(), [metric]].copy()
    valid["date"] = dates[dates.notna()].dt.to_period("M").astype(str)
    if valid.empty:
        return []
    return records(valid.groupby("date")[metric].sum().reset_index().sort_values("date"), limit=120)


def build_scatter(dataframe: pd.DataFrame, roles: dict[str, str]) -> list[dict]:
    revenue = roles.get("revenue")
    profit = roles.get("profit")
    quantity = roles.get("quantity")
    product = roles.get("product")
    x_axis = profit or quantity
    if not revenue or not x_axis or dataframe.empty:
        return []
    columns = [column for column in [product, revenue, x_axis, roles.get("category"), roles.get("region")] if column]
    return records(dataframe[columns].dropna(subset=[revenue, x_axis]).sort_values(revenue, ascending=False), limit=250)


def build_correlation_heatmap(dataframe: pd.DataFrame) -> list[dict]:
    numeric_columns = [column for column in dataframe.columns if is_numeric_dtype(dataframe[column])]
    if len(numeric_columns) < 2:
        return []
    matrix = dataframe[numeric_columns].corr().round(4).reset_index().rename(columns={"index": "column"})
    return records(matrix, limit=len(matrix))


def build_interactive_dashboard(dataframe: pd.DataFrame, filters: DashboardFilters | None = None) -> dict[str, Any]:
    filters = filters or DashboardFilters()
    roles = detect_dashboard_roles(dataframe)
    filtered = apply_filters(dataframe, roles, filters)
    revenue = roles.get("revenue")
    profit = roles.get("profit")
    order = roles.get("order")
    quantity = roles.get("quantity")
    metric = revenue or profit or quantity

    kpis = {
        "rows": int(len(filtered)),
        "revenue": safe_total(filtered, revenue),
        "profit": safe_total(filtered, profit),
        "quantity": safe_total(filtered, quantity),
        "orders": int(filtered[order].nunique()) if order and order in filtered else int(len(filtered)),
    }
    if kpis["orders"] and revenue:
        kpis["average_order_value"] = float(kpis["revenue"] / kpis["orders"])

    category = roles.get("category")
    region = roles.get("region")
    product = roles.get("product")
    customer_segment = roles.get("customer_segment")

    return {
        "detected_roles": roles,
        "filters": build_filter_options(dataframe, roles),
        "active_filters": {key: value for key, value in filters.__dict__.items() if value not in (None, "")},
        "kpis": kpis,
        "trend": build_trend(filtered, roles.get("date"), metric),
        "category_breakdown": aggregate_dimension(filtered, category, metric),
        "subcategory_breakdown": aggregate_dimension(filtered, roles.get("subcategory"), metric),
        "region_breakdown": aggregate_dimension(filtered, region, metric),
        "state_breakdown": aggregate_dimension(filtered, roles.get("state"), metric),
        "product_breakdown": aggregate_dimension(filtered, product, metric),
        "customer_segment_breakdown": aggregate_dimension(filtered, customer_segment, metric),
        "scatter": build_scatter(filtered, roles),
        "treemap": records(
            filtered[[column for column in [category, product, metric] if column]].dropna().sort_values(metric, ascending=False),
            limit=250,
        ) if category and product and metric and not filtered.empty else [],
        "bubble": aggregate_dimension(filtered, product, revenue, limit=50) if product and revenue else [],
        "correlation_heatmap": build_correlation_heatmap(filtered),
        "record_count": int(len(filtered)),
    }
