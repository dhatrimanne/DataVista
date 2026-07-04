from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype


@dataclass(frozen=True)
class CleaningResult:
    dataframe: pd.DataFrame
    report: dict[str, Any]


def normalize_column_name(column: object) -> str:
    name = str(column).strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_") or "column"


def dedupe_column_names(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for column in columns:
        count = seen.get(column, 0)
        result.append(column if count == 0 else f"{column}_{count + 1}")
        seen[column] = count + 1
    return result


def try_convert_types(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    converted = dataframe.copy()
    conversions: dict[str, str] = {}
    for column in converted.columns:
        series = converted[column]
        if series.dtype != "object" and not is_string_dtype(series):
            continue

        non_missing_total = max(int(series.notna().sum()), 1)
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_ratio = int(numeric.notna().sum()) / non_missing_total
        if numeric_ratio >= 0.85:
            converted[column] = numeric
            conversions[column] = "numeric"
            continue

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            parsed_dates = pd.to_datetime(series, errors="coerce", utc=False)
        date_ratio = int(parsed_dates.notna().sum()) / non_missing_total
        if date_ratio >= 0.85:
            converted[column] = parsed_dates
            conversions[column] = "datetime"
    return converted, conversions


def outlier_mask_iqr(dataframe: pd.DataFrame) -> tuple[pd.Series, dict[str, int]]:
    if dataframe.empty:
        return pd.Series([False] * len(dataframe), index=dataframe.index), {}

    combined_mask = pd.Series(False, index=dataframe.index)
    counts: dict[str, int] = {}
    for column in dataframe.columns:
        if not is_numeric_dtype(dataframe[column]):
            continue
        values = dataframe[column].dropna()
        if values.empty:
            continue
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (dataframe[column] < lower) | (dataframe[column] > upper)
        count = int(mask.sum())
        if count:
            counts[column] = count
            combined_mask = combined_mask | mask
    return combined_mask, counts


def fill_missing_values(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    cleaned = dataframe.copy()
    strategies: dict[str, str] = {}
    for column in cleaned.columns:
        missing_count = int(cleaned[column].isna().sum())
        if missing_count == 0:
            continue

        if is_numeric_dtype(cleaned[column]):
            fill_value = cleaned[column].median()
            if pd.isna(fill_value):
                fill_value = 0
            cleaned[column] = cleaned[column].fillna(fill_value)
            strategies[column] = "median"
        elif pd.api.types.is_datetime64_any_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].ffill().bfill()
            strategies[column] = "forward/backward fill"
        else:
            mode = cleaned[column].mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else "Unknown"
            cleaned[column] = cleaned[column].fillna(fill_value)
            strategies[column] = "mode"
    return cleaned, strategies


def build_quality_components(report: dict[str, Any]) -> dict[str, Any]:
    initial_rows = max(report["initial_shape"]["rows"], 1)
    initial_cells = max(report["initial_shape"]["rows"] * report["initial_shape"]["columns"], 1)
    missing_ratio = report["initial_missing_values"] / initial_cells
    duplicate_ratio = report["duplicates_removed"] / initial_rows
    outlier_ratio = report["outliers_detected"] / initial_rows
    removed_column_ratio = (
        (len(report["empty_columns_removed"]) + len(report["constant_columns_removed"]))
        / max(report["initial_shape"]["columns"], 1)
    )

    penalty = (missing_ratio * 35) + (duplicate_ratio * 25) + (outlier_ratio * 20) + (removed_column_ratio * 20)
    completeness = 1 - missing_ratio
    return {
        "missing_value_ratio": round(missing_ratio, 4),
        "duplicate_ratio": round(duplicate_ratio, 4),
        "outlier_ratio": round(outlier_ratio, 4),
        "removed_column_ratio": round(removed_column_ratio, 4),
        "completeness": round(completeness, 4),
        "invalid_type_columns": list(report["type_conversions"].keys()),
        "penalty": round(penalty, 2),
    }


def build_quality_recommendations(report: dict[str, Any], components: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if components["missing_value_ratio"] > 0:
        recommendations.append("Review upstream collection fields that produced missing values before imputation.")
    if components["duplicate_ratio"] > 0:
        recommendations.append("Add a source-system uniqueness check to reduce duplicate business records.")
    if components["outlier_ratio"] > 0:
        recommendations.append("Validate outlier records with business owners before using them in forecasting.")
    if components["removed_column_ratio"] > 0:
        recommendations.append("Remove empty or constant export columns from the source report configuration.")
    if components["invalid_type_columns"]:
        recommendations.append("Standardize source column formats for " + ", ".join(components["invalid_type_columns"]) + ".")
    if not recommendations:
        recommendations.append("No major data quality issues were detected in this upload.")
    return recommendations


def calculate_quality_score(report: dict[str, Any]) -> int:
    penalty = build_quality_components(report)["penalty"]
    return max(0, min(100, round(100 - penalty)))


def clean_dataframe(dataframe: pd.DataFrame, remove_outliers: bool = False) -> CleaningResult:
    report: dict[str, Any] = {
        "initial_shape": {"rows": int(dataframe.shape[0]), "columns": int(dataframe.shape[1])},
        "initial_missing_values": int(dataframe.isna().sum().sum()),
        "columns_normalized": {},
        "whitespace_trimmed_columns": [],
        "empty_columns_removed": [],
        "constant_columns_removed": [],
        "duplicates_removed": 0,
        "type_conversions": {},
        "missing_value_strategy": {},
        "outliers_detected_by_column": {},
        "outliers_detected": 0,
        "outliers_removed": 0,
        "remove_outliers": remove_outliers,
    }

    cleaned = dataframe.copy()
    normalized_columns = dedupe_column_names([normalize_column_name(column) for column in cleaned.columns])
    report["columns_normalized"] = {
        str(original): normalized
        for original, normalized in zip(cleaned.columns, normalized_columns, strict=False)
        if str(original) != normalized
    }
    cleaned.columns = normalized_columns
    cleaned = cleaned.replace([np.inf, -np.inf], pd.NA)

    for column in cleaned.select_dtypes(include=["object", "str"]).columns:
        trimmed = cleaned[column].map(lambda value: value.strip() if isinstance(value, str) else value)
        if not trimmed.equals(cleaned[column]):
            report["whitespace_trimmed_columns"].append(column)
            cleaned[column] = trimmed

    empty_columns = [column for column in cleaned.columns if cleaned[column].isna().all()]
    if empty_columns:
        cleaned = cleaned.drop(columns=empty_columns)
        report["empty_columns_removed"] = empty_columns

    constant_columns = [
        column
        for column in cleaned.columns
        if cleaned[column].nunique(dropna=True) <= 1 and not cleaned[column].isna().any()
    ]
    if constant_columns:
        cleaned = cleaned.drop(columns=constant_columns)
        report["constant_columns_removed"] = constant_columns

    cleaned, conversions = try_convert_types(cleaned)
    report["type_conversions"] = conversions

    outlier_mask, outlier_counts = outlier_mask_iqr(cleaned)
    report["outliers_detected_by_column"] = outlier_counts
    report["outliers_detected"] = int(outlier_mask.sum())
    if remove_outliers and report["outliers_detected"]:
        cleaned = cleaned.loc[~outlier_mask].copy()
        report["outliers_removed"] = int(outlier_mask.sum())

    cleaned, missing_strategy = fill_missing_values(cleaned)
    report["missing_value_strategy"] = missing_strategy

    before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    report["duplicates_removed"] = int(before_dedup - len(cleaned))

    report["final_shape"] = {"rows": int(cleaned.shape[0]), "columns": int(cleaned.shape[1])}
    report["final_missing_values"] = int(cleaned.isna().sum().sum())
    report["quality_components"] = build_quality_components(report)
    report["quality_recommendations"] = build_quality_recommendations(report, report["quality_components"])
    report["data_quality_score"] = calculate_quality_score(report)

    return CleaningResult(dataframe=cleaned, report=report)
