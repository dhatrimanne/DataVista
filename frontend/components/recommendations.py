from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.utils import api


def render_recommendations(token: str) -> None:
    st.subheader("Smart recommendations")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not datasets:
        st.caption("Upload a dataset to generate recommendations.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
        key="recommendations_dataset",
    )

    try:
        payload = api.get_recommendations(token, selected_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    summary = payload["summary"]
    cols = st.columns(2)
    cols[0].metric("Recommendations", summary["total"])
    cols[1].metric("Categories", len(summary["covered_categories"]))

    if summary["unsupported"]:
        st.info(" ".join(summary["unsupported"]))
        return

    grouped: dict[str, list[dict]] = {}
    for item in payload["recommendations"]:
        grouped.setdefault(item["category"], []).append(item)

    for category, items in grouped.items():
        st.write(category)
        rows = [
            {
                "Title": item["title"],
                "Rationale": item["rationale"],
                "Evidence": item["evidence"],
            }
            for item in items
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
