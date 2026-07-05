import streamlit as st

from utils import api


def show_error(message: str) -> None:
    st.error(message or "The request could not be completed. Please try again.")


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def render_upload(token: str) -> None:
    uploaded_file = st.file_uploader("Upload dataset", type=["csv", "xlsx", "xls"])
    if uploaded_file is None:
        return
    remove_outliers = st.checkbox("Remove outliers during cleaning", value=False, key="upload_remove_outliers")
    processing_key = "dataset_upload_processing"

    if st.button("Upload dataset", use_container_width=True, disabled=st.session_state.get(processing_key, False)):
        st.session_state[processing_key] = True
        try:
            with st.status("Processing dataset...", expanded=True) as status:
                st.write("Uploading dataset...")
                st.write("Cleaning dataset...")
                st.write("Detecting data types...")
                st.write("Running exploratory analysis...")
                st.write("Generating dashboard...")
                st.write("Calculating business health...")
                st.write("Calculating data quality...")
                st.write("Generating recommendations...")
                st.write("Saving results...")
                api.upload_dataset(token, uploaded_file.name, uploaded_file.getvalue(), remove_outliers=remove_outliers)
                status.update(label="Completed successfully.", state="complete", expanded=False)
            st.success("Dataset uploaded successfully.")
            st.rerun()
        except api.ApiError as exc:
            show_error(str(exc))
        finally:
            st.session_state[processing_key] = False


def dataset_rows(datasets: list[dict]) -> list[dict]:
    return [
        {
            "ID": dataset["id"],
            "Name": dataset["name"],
            "Uploaded file": dataset["original_filename"],
            "Size": format_bytes(dataset["file_size_bytes"]),
            "Rows": dataset["row_count"],
            "Columns": dataset["column_count"],
            "Missing values": dataset["missing_value_count"],
            "Quality": dataset.get("data_quality_score"),
            "Status": dataset["status"],
            "Uploaded": dataset["created_at"],
        }
        for dataset in datasets
    ]


def render_dataset_actions(token: str, dataset: dict) -> None:
    with st.expander(f"{dataset['name']} controls", expanded=False):
        new_name = st.text_input("Dataset name", value=dataset["name"], key=f"name_{dataset['id']}")
        remove_outliers = st.checkbox(
            "Remove outliers on re-analysis",
            value=False,
            key=f"remove_outliers_{dataset['id']}",
        )
        col_a, col_b, col_c, col_d = st.columns(4)

        if col_a.button("Rename", key=f"rename_{dataset['id']}", use_container_width=True):
            try:
                api.rename_dataset(token, dataset["id"], new_name)
                st.success("Dataset renamed.")
                st.rerun()
            except api.ApiError as exc:
                show_error(str(exc))

        reanalyze_key = f"reanalyze_processing_{dataset['id']}"
        if col_b.button(
            "Re-analyze",
            key=f"reanalyze_{dataset['id']}",
            use_container_width=True,
            disabled=st.session_state.get(reanalyze_key, False),
        ):
            st.session_state[reanalyze_key] = True
            try:
                with st.spinner("Cleaning and analyzing dataset..."):
                    api.reanalyze_dataset(token, dataset["id"], remove_outliers=remove_outliers)
                st.success("Dataset re-analyzed.")
                st.rerun()
            except api.ApiError as exc:
                show_error(str(exc))
            finally:
                st.session_state[reanalyze_key] = False

        try:
            cleaned_content = api.download_cleaned_dataset(token, dataset["id"])
            col_c.download_button(
                "Download cleaned",
                cleaned_content,
                file_name=f"{dataset['name']}_cleaned.csv",
                mime="text/csv",
                key=f"download_{dataset['id']}",
                use_container_width=True,
            )
        except api.ApiError:
            col_c.button("Download cleaned", key=f"download_disabled_{dataset['id']}", disabled=True)

        if col_d.button("Delete", key=f"delete_{dataset['id']}", use_container_width=True):
            try:
                api.delete_dataset(token, dataset["id"])
                st.success("Dataset deleted.")
                st.rerun()
            except api.ApiError as exc:
                show_error(str(exc))

        try:
            detail = api.get_dataset_detail(token, dataset["id"])
        except api.ApiError as exc:
            show_error(str(exc))
            return

        st.write("History")
        if not detail["history"]:
            st.caption("No history yet.")
        else:
            st.dataframe(detail["history"], hide_index=True, use_container_width=True)

        render_cleaning_report(detail.get("cleaning_report"))


def render_cleaning_report(report: dict | None) -> None:
    st.write("Cleaning report")
    if not report:
        st.caption("No cleaning report available.")
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("Quality score", report.get("data_quality_score", 0))
    metric_cols[1].metric("Duplicates removed", report.get("duplicates_removed", 0))
    metric_cols[2].metric("Outliers detected", report.get("outliers_detected", 0))
    metric_cols[3].metric("Outliers removed", report.get("outliers_removed", 0))

    shape_rows = [
        {"Stage": "Initial", **report["initial_shape"], "missing_values": report["initial_missing_values"]},
        {"Stage": "Final", **report["final_shape"], "missing_values": report["final_missing_values"]},
    ]
    st.dataframe(shape_rows, hide_index=True, use_container_width=True)

    actions = [
        {"Action": "Empty columns removed", "Details": ", ".join(report["empty_columns_removed"]) or "None"},
        {"Action": "Constant columns removed", "Details": ", ".join(report["constant_columns_removed"]) or "None"},
        {
            "Action": "Whitespace trimmed",
            "Details": ", ".join(report["whitespace_trimmed_columns"]) or "None",
        },
        {
            "Action": "Type conversions",
            "Details": ", ".join(f"{key}: {value}" for key, value in report["type_conversions"].items()) or "None",
        },
        {
            "Action": "Missing values",
            "Details": ", ".join(f"{key}: {value}" for key, value in report["missing_value_strategy"].items()) or "None",
        },
        {
            "Action": "Outliers",
            "Details": ", ".join(
                f"{key}: {value}" for key, value in report["outliers_detected_by_column"].items()
            )
            or "None",
        },
    ]
    st.dataframe(actions, hide_index=True, use_container_width=True)

    components = report.get("quality_components", {})
    if components:
        st.write("Quality score breakdown")
        breakdown = [
            {"Metric": key.replace("_", " ").title(), "Value": value}
            for key, value in components.items()
            if key != "invalid_type_columns"
        ]
        breakdown.append({"Metric": "Invalid Type Columns", "Value": ", ".join(components["invalid_type_columns"]) or "None"})
        st.dataframe(breakdown, hide_index=True, use_container_width=True)

    recommendations = report.get("quality_recommendations", [])
    if recommendations:
        st.write("Recommendations")
        st.dataframe([{"Recommendation": recommendation} for recommendation in recommendations], hide_index=True, use_container_width=True)


def render_dataset_manager(token: str) -> None:
    st.subheader("Dataset management")
    render_upload(token)

    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        show_error(str(exc))
        return

    if not datasets:
        st.info("No datasets uploaded yet. Upload a CSV or Excel file to generate analytics, dashboards, ML models, and reports.")
        return

    st.dataframe(dataset_rows(datasets), hide_index=True, use_container_width=True)
    for dataset in datasets:
        render_dataset_actions(token, dataset)
