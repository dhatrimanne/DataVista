from __future__ import annotations

import streamlit as st

from frontend.components.datasets import format_bytes
from frontend.utils import api


def render_report_center(token: str) -> None:
    st.subheader("Report center")
    try:
        datasets = api.list_datasets(token)
        reports = api.list_reports(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if datasets:
        selected_id = st.selectbox(
            "Dataset",
            options=[dataset["id"] for dataset in datasets],
            format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
            key="report_dataset",
        )
        include_ai = st.checkbox("Include Gemini AI insights", value=False)
        processing_key = f"report_processing_{selected_id}"
        if st.button("Generate PDF report", type="primary", disabled=st.session_state.get(processing_key, False)):
            st.session_state[processing_key] = True
            try:
                with st.spinner("Generating executive PDF report..."):
                    api.create_report(token, selected_id, include_ai_insights=include_ai)
                st.success("Report generated.")
                st.rerun()
            except api.ApiError as exc:
                st.warning(str(exc))
            finally:
                st.session_state[processing_key] = False
    else:
        st.caption("Upload a dataset to generate reports.")

    st.write("Report history")
    if not reports:
        st.info("No reports generated yet. Generate your first business report to download executive-ready insights.")
        return

    rows = [
        {
            "ID": report["id"],
            "Title": report["title"],
            "Dataset ID": report["dataset_id"],
            "Size": format_bytes(report["file_size_bytes"]),
            "Created": report["created_at"],
        }
        for report in reports
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    for report in reports:
        with st.expander(report["title"]):
            columns = st.columns(2)
            try:
                content = api.download_report(token, report["id"])
                columns[0].download_button(
                    "Download PDF",
                    content,
                    file_name=f"{report['title']}.pdf",
                    mime="application/pdf",
                    key=f"report_download_{report['id']}",
                    use_container_width=True,
                )
            except api.ApiError:
                columns[0].button("Download PDF", disabled=True, key=f"report_download_disabled_{report['id']}")

            if columns[1].button("Delete", key=f"report_delete_{report['id']}", use_container_width=True):
                try:
                    api.delete_report(token, report["id"])
                    st.success("Report deleted.")
                    st.rerun()
                except api.ApiError as exc:
                    st.error(str(exc))
