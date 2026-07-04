from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype


ROLE_ALIASES = {
    "date": ("order_date", "date", "transaction_date", "invoice_date", "sale_date"),
    "revenue": ("revenue", "sales", "amount", "total_sales", "sales_amount"),
    "profit": ("profit", "net_profit", "gross_profit"),
    "order": ("order_id", "order", "invoice_id", "transaction_id"),
    "customer": ("customer_id", "customer_name", "customer", "client_id"),
    "product": ("product_name", "product", "item_name", "item", "sku"),
    "category": ("category", "product_category"),
    "region": ("region", "state", "country", "territory", "market"),
    "quantity": ("quantity", "qty", "units", "units_sold"),
}


def json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def records(dataframe: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    return [
        {str(key): json_value(value) for key, value in row.items()}
        for row in dataframe.head(limit).to_dict(orient="records")
    ]


def detect_roles(dataframe: pd.DataFrame) -> dict[str, str]:
    columns = list(dataframe.columns)
    detected: dict[str, str] = {}
    for role, aliases in ROLE_ALIASES.items():
        exact = next((column for column in columns if column in aliases), None)
        if exact:
            detected[role] = exact
            continue
        partial = next((column for column in columns if any(alias in column for alias in aliases)), None)
        if partial:
            detected[role] = partial
    return detected


def aggregate_ranking(dataframe: pd.DataFrame, dimension: str, metric: str, ascending: bool = False) -> list[dict]:
    grouped = (
        dataframe.groupby(dimension, dropna=False)[metric]
        .sum()
        .sort_values(ascending=ascending)
        .reset_index()
    )
    return records(grouped, limit=10)


def build_time_analysis(dataframe: pd.DataFrame, date_column: str, metric: str) -> dict[str, list[dict]]:
    dates = pd.to_datetime(dataframe[date_column], errors="coerce")
    valid = dataframe.loc[dates.notna(), [metric]].copy()
    valid["date"] = dates[dates.notna()]
    if valid.empty:
        return {}

    return {
        "monthly": records(valid.groupby(valid["date"].dt.to_period("M").astype(str))[metric].sum().reset_index()),
        "quarterly": records(valid.groupby(valid["date"].dt.to_period("Q").astype(str))[metric].sum().reset_index()),
        "yearly": records(valid.groupby(valid["date"].dt.year)[metric].sum().reset_index()),
        "weekly": records(valid.groupby(valid["date"].dt.to_period("W").astype(str))[metric].sum().reset_index()),
    }


def build_customer_analysis(dataframe: pd.DataFrame, roles: dict[str, str]) -> dict[str, Any]:
    customer = roles.get("customer")
    revenue = roles.get("revenue")
    if not customer or not revenue:
        return {}

    grouped = dataframe.groupby(customer, dropna=False).agg(
        revenue=(revenue, "sum"),
        orders=(roles.get("order", revenue), "nunique" if roles.get("order") else "count"),
    ).reset_index()
    grouped["value_segment"] = pd.qcut(
        grouped["revenue"].rank(method="first"),
        q=min(3, len(grouped)),
        labels=["Low Value", "Medium Value", "High Value"][-min(3, len(grouped)):],
    ).astype(str) if len(grouped) > 1 else "High Value"

    result: dict[str, Any] = {
        "top_customers": records(grouped.sort_values("revenue", ascending=False), 10),
        "segments": records(grouped.groupby("value_segment", observed=True).agg(customers=(customer, "count"), revenue=("revenue", "sum")).reset_index()),
        "repeat_customers": int((grouped["orders"] > 1).sum()),
        "customer_lifetime_value_average": float(grouped["revenue"].mean()),
    }

    date = roles.get("date")
    if date:
        parsed = pd.to_datetime(dataframe[date], errors="coerce")
        latest = parsed.max()
        if pd.notna(latest):
            rfm_source = dataframe.assign(_date=parsed).dropna(subset=["_date"])
            rfm = rfm_source.groupby(customer).agg(
                recency=("_date", lambda values: int((latest - values.max()).days)),
                frequency=(roles.get("order", revenue), "nunique" if roles.get("order") else "count"),
                monetary=(revenue, "sum"),
            ).reset_index()
            result["rfm"] = records(rfm.sort_values(["monetary", "frequency"], ascending=False), 20)
    return result


def analyze_dataframe(dataframe: pd.DataFrame) -> dict[str, Any]:
    roles = detect_roles(dataframe)
    revenue = roles.get("revenue")
    profit = roles.get("profit")
    order = roles.get("order")
    numeric_columns = [column for column in dataframe.columns if is_numeric_dtype(dataframe[column])]

    kpis: dict[str, Any] = {}
    if revenue:
        kpis["revenue"] = float(dataframe[revenue].sum())
    if profit:
        kpis["profit"] = float(dataframe[profit].sum())
    if order:
        kpis["orders"] = int(dataframe[order].nunique())
    if revenue and kpis.get("orders"):
        kpis["average_order_value"] = float(kpis["revenue"] / kpis["orders"])

    product_analysis: dict[str, Any] = {}
    if roles.get("product") and revenue:
        product_analysis["best_sellers"] = aggregate_ranking(dataframe, roles["product"], revenue)
        product_analysis["worst_sellers"] = aggregate_ranking(dataframe, roles["product"], revenue, ascending=True)
    if roles.get("product") and profit:
        product_analysis["most_profitable"] = aggregate_ranking(dataframe, roles["product"], profit)
        product_analysis["least_profitable"] = aggregate_ranking(dataframe, roles["product"], profit, ascending=True)

    regional_analysis = {}
    if roles.get("region") and revenue:
        regional_analysis["performance"] = aggregate_ranking(dataframe, roles["region"], revenue)

    metric = revenue or profit or (numeric_columns[0] if numeric_columns else None)
    time_analysis = build_time_analysis(dataframe, roles["date"], metric) if roles.get("date") and metric else {}

    correlation = []
    if len(numeric_columns) >= 2:
        matrix = dataframe[numeric_columns].corr().round(4).reset_index().rename(columns={"index": "column"})
        correlation = records(matrix, limit=len(matrix))

    distributions = []
    for column in numeric_columns[:8]:
        series = dataframe[column].dropna()
        distributions.append({
            "column": column,
            "count": int(series.count()),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
        })

    supported = [name for name, value in {
        "sales": kpis,
        "customer": build_customer_analysis(dataframe, roles),
        "product": product_analysis,
        "regional": regional_analysis,
        "time": time_analysis,
        "statistical": correlation or distributions,
    }.items() if value]
    unavailable = [section for section in ("sales", "customer", "product", "regional", "time", "statistical") if section not in supported]

    return {
        "detected_roles": roles,
        "kpis": kpis,
        "customer_analysis": build_customer_analysis(dataframe, roles),
        "product_analysis": product_analysis,
        "regional_analysis": regional_analysis,
        "time_analysis": time_analysis,
        "statistical_analysis": {"correlation": correlation, "distributions": distributions},
        "supported_sections": supported,
        "unavailable_sections": unavailable,
    }
