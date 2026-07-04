from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_curve,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from backend.analytics.eda import detect_roles, json_value, records


CHURN_ALIASES = ("churn", "churned", "is_churned", "customer_churn", "cancelled", "canceled")


def unavailable(reason: str, required_data: list[str]) -> dict[str, Any]:
    return {"available": False, "reason": reason, "required_data": required_data}


def detect_churn_column(dataframe: pd.DataFrame) -> str | None:
    columns = list(dataframe.columns)
    return next((column for column in columns if column in CHURN_ALIASES), None)


def build_sales_forecast(dataframe: pd.DataFrame, periods: int = 3) -> dict[str, Any]:
    roles = detect_roles(dataframe)
    date_column = roles.get("date")
    revenue_column = roles.get("revenue")
    if not date_column or not revenue_column:
        return unavailable(
            "Sales forecasting requires a date column and a revenue or sales column.",
            ["order_date/date", "revenue/sales"],
        )

    dates = pd.to_datetime(dataframe[date_column], errors="coerce")
    source = dataframe.loc[dates.notna(), [revenue_column]].copy()
    source["date"] = dates[dates.notna()].dt.to_period("M").dt.to_timestamp()
    monthly = source.groupby("date", as_index=False)[revenue_column].sum().sort_values("date")
    if len(monthly) < 3:
        return unavailable(
            "Sales forecasting requires at least three dated periods after cleaning.",
            ["three or more months/weeks of revenue history"],
        )

    monthly["period_index"] = np.arange(len(monthly))
    x = monthly[["period_index"]]
    y = monthly[revenue_column]
    split_index = max(1, int(len(monthly) * 0.8))
    train_x, test_x = x.iloc[:split_index], x.iloc[split_index:]
    train_y, test_y = y.iloc[:split_index], y.iloc[split_index:]

    model = LinearRegression()
    model.fit(train_x, train_y)
    evaluation_x = test_x if not test_x.empty else train_x
    evaluation_y = test_y if not test_y.empty else train_y
    predictions = model.predict(evaluation_x)

    future_index = np.arange(len(monthly), len(monthly) + periods)
    future_dates = pd.date_range(monthly["date"].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    future_predictions = model.predict(pd.DataFrame({"period_index": future_index}))

    return {
        "available": True,
        "model": "Linear Regression",
        "target": revenue_column,
        "history": records(monthly[["date", revenue_column]], limit=len(monthly)),
        "forecast": [
            {"date": date.date().isoformat(), "predicted_sales": max(0.0, float(value))}
            for date, value in zip(future_dates, future_predictions, strict=False)
        ],
        "metrics": {
            "rmse": float(np.sqrt(mean_squared_error(evaluation_y, predictions))),
            "mae": float(mean_absolute_error(evaluation_y, predictions)),
            "r2": float(r2_score(evaluation_y, predictions)) if len(evaluation_y) > 1 else 1.0,
        },
        "trend_line": {
            "slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
        },
    }


def build_customer_churn(dataframe: pd.DataFrame) -> dict[str, Any]:
    churn_column = detect_churn_column(dataframe)
    if not churn_column:
        return unavailable(
            "Customer churn requires a binary churn label column.",
            ["churn/churned/is_churned column with 0 and 1 values"],
        )

    labels = pd.to_numeric(dataframe[churn_column], errors="coerce")
    numeric_columns = [
        column
        for column in dataframe.columns
        if column != churn_column and is_numeric_dtype(dataframe[column])
    ]
    source = dataframe[numeric_columns].copy()
    source[churn_column] = labels
    source = source.dropna()
    if len(source) < 6 or source[churn_column].nunique() < 2 or not numeric_columns:
        return unavailable(
            "Customer churn requires enough numeric features and both churned and retained examples.",
            ["binary churn labels", "numeric customer behavior features", "at least six usable rows"],
        )

    x = source[numeric_columns]
    y = source[churn_column].astype(int)
    stratify = y if y.value_counts().min() >= 2 else None
    train_x, test_x, train_y, test_y = train_test_split(x, y, test_size=0.35, random_state=42, stratify=stratify)

    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train_x)
    test_scaled = scaler.transform(test_x)
    model = LogisticRegression(max_iter=1000)
    model.fit(train_scaled, train_y)
    predicted = model.predict(test_scaled)
    probabilities = model.predict_proba(test_scaled)[:, 1]
    fpr, tpr, thresholds = roc_curve(test_y, probabilities)

    scored = source.copy()
    scored["churn_risk"] = model.predict_proba(scaler.transform(source[numeric_columns]))[:, 1]
    high_risk = scored.sort_values("churn_risk", ascending=False).head(10)

    return {
        "available": True,
        "model": "Logistic Regression",
        "target": churn_column,
        "features": numeric_columns,
        "high_risk_customers": records(high_risk, limit=10),
        "confusion_matrix": confusion_matrix(test_y, predicted).tolist(),
        "roc_curve": [
            {"fpr": float(f), "tpr": float(t), "threshold": json_value(threshold)}
            for f, t, threshold in zip(fpr, tpr, thresholds, strict=False)
        ],
        "metrics": {
            "accuracy": float(accuracy_score(test_y, predicted)),
            "precision": float(precision_score(test_y, predicted, zero_division=0)),
            "recall": float(recall_score(test_y, predicted, zero_division=0)),
            "f1": float(f1_score(test_y, predicted, zero_division=0)),
        },
    }


def build_customer_segmentation(dataframe: pd.DataFrame) -> dict[str, Any]:
    roles = detect_roles(dataframe)
    customer = roles.get("customer")
    revenue = roles.get("revenue")
    if not customer or not revenue:
        return unavailable(
            "Customer segmentation requires customer identifiers and revenue values.",
            ["customer_id/customer column", "revenue/sales column"],
        )

    aggregations: dict[str, tuple[str, str]] = {"revenue": (revenue, "sum")}
    if roles.get("profit"):
        aggregations["profit"] = (roles["profit"], "sum")
    if roles.get("order"):
        aggregations["orders"] = (roles["order"], "nunique")
    grouped = dataframe.groupby(customer).agg(**aggregations).reset_index()
    feature_columns = [column for column in ("revenue", "profit", "orders") if column in grouped]
    if len(grouped) < 3:
        return unavailable(
            "Customer segmentation requires at least three customers.",
            ["three or more customers with revenue history"],
        )

    scaled = StandardScaler().fit_transform(grouped[feature_columns])
    candidates = range(2, min(6, len(grouped) - 1) + 1)
    scores: list[dict[str, Any]] = []
    best_k = 2
    best_score = -1.0
    for k in candidates:
        model = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = model.fit_predict(scaled)
        score = silhouette_score(scaled, labels) if len(set(labels)) > 1 else -1.0
        inertia = float(model.inertia_)
        scores.append({"k": k, "inertia": inertia, "silhouette": float(score)})
        if score > best_score:
            best_k = k
            best_score = float(score)

    model = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
    grouped["cluster"] = model.fit_predict(scaled)
    cluster_values = grouped.groupby("cluster")["revenue"].mean().sort_values()
    names = ["Low Value", "Medium Value", "High Value"]
    label_map = {
        cluster: names[min(index, len(names) - 1)]
        for index, cluster in enumerate(cluster_values.index.tolist())
    }
    grouped["segment"] = grouped["cluster"].map(label_map)

    return {
        "available": True,
        "model": "K-Means",
        "features": feature_columns,
        "optimal_clusters": int(best_k),
        "elbow": scores,
        "silhouette_score": float(best_score),
        "segments": records(grouped.sort_values("revenue", ascending=False), limit=100),
        "segment_summary": records(
            grouped.groupby("segment", observed=True).agg(customers=(customer, "count"), revenue=("revenue", "sum")).reset_index(),
            limit=10,
        ),
    }
