import pandas as pd

from backend.analytics.cleaning import clean_dataframe


def test_clean_dataframe_normalizes_and_reports_core_actions():
    dataframe = pd.DataFrame(
        {
            " Order Date ": ["2026-01-01", "2026-01-01", "2026-02-01"],
            " Revenue ": ["100", "100", None],
            " Region ": [" North ", " North ", None],
            " Empty ": [None, None, None],
            " Constant ": ["same", "same", "same"],
        }
    )

    result = clean_dataframe(dataframe)
    report = result.report

    assert list(result.dataframe.columns) == ["order_date", "revenue", "region"]
    assert result.dataframe.shape == (2, 3)
    assert int(result.dataframe.isna().sum().sum()) == 0
    assert report["duplicates_removed"] == 1
    assert report["empty_columns_removed"] == ["empty"]
    assert report["constant_columns_removed"] == ["constant"]
    assert report["type_conversions"]["order_date"] == "datetime"
    assert report["type_conversions"]["revenue"] == "numeric"
    assert report["missing_value_strategy"]["revenue"] == "median"
    assert report["missing_value_strategy"]["region"] == "mode"
    assert report["data_quality_score"] < 100
    assert report["quality_components"]["missing_value_ratio"] > 0
    assert "revenue" in report["quality_components"]["invalid_type_columns"]
    assert report["quality_recommendations"]


def test_clean_dataframe_can_remove_outliers():
    dataframe = pd.DataFrame({"revenue": [10, 11, 12, 13, 1000], "region": ["A", "A", "A", "A", "B"]})

    detected = clean_dataframe(dataframe, remove_outliers=False)
    removed = clean_dataframe(dataframe, remove_outliers=True)

    assert detected.report["outliers_detected"] == 1
    assert detected.report["outliers_removed"] == 0
    assert detected.report["quality_components"]["outlier_ratio"] > 0
    assert any("outlier" in recommendation.lower() for recommendation in detected.report["quality_recommendations"])
    assert removed.report["outliers_removed"] == 1
    assert removed.dataframe["revenue"].max() == 13
