from __future__ import annotations

import streamlit as st

from frontend.components.ai_typography import inject_ai_typography, render_ai_markdown
from frontend.utils import api


def render_ai_insights(token: str) -> None:
    inject_ai_typography()
    st.subheader("AI business insights")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not datasets:
        st.caption("Upload a dataset to generate AI insights.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
        key="ai_insights_dataset",
    )

    processing_key = f"ai_insights_processing_{selected_id}"
    if st.button("Generate insights", type="primary", disabled=st.session_state.get(processing_key, False)):
        st.session_state[processing_key] = True
        try:
            with st.spinner("Generating insights with Gemini..."):
                st.session_state["ai_insights_result"] = api.generate_business_insights(token, selected_id)
                st.session_state["ai_insights_dataset_id"] = selected_id
        except api.ApiError as exc:
            st.warning(str(exc))
            return
        finally:
            st.session_state[processing_key] = False

    result = st.session_state.get("ai_insights_result")
    if not result or st.session_state.get("ai_insights_dataset_id") != selected_id:
        st.caption("Generate insights to view executive summary, recommendations, risks, and next-quarter strategy.")
        return

    summary = result["context_summary"]
    cols = st.columns(3)
    cols[0].metric("Rows analyzed", f"{summary['rows']:,}")
    cols[1].metric("Columns", summary["columns"])
    cols[2].metric("Sections", len(summary["analysis_sections"]))
    render_ai_markdown(result["insights"], key="ai_insights_copy")
