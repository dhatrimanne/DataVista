from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import api


def unavailable_panel(result: dict) -> None:
    st.info(result.get("reason", "This model cannot be trained for the selected dataset."))
    required = result.get("required_data", [])
    if required:
        st.write("Required data: " + ", ".join(required))


def render_sales_forecast(result: dict) -> None:
    st.subheader("Sales forecasting")
    if not result.get("available"):
        unavailable_panel(result)
        return

    metrics = result["metrics"]
    cols = st.columns(3)
    cols[0].metric("RMSE", f"{metrics['rmse']:,.2f}")
    cols[1].metric("MAE", f"{metrics['mae']:,.2f}")
    cols[2].metric("R2", f"{metrics['r2']:,.3f}")

    history = pd.DataFrame(result["history"]).rename(columns={result["target"]: "sales"})
    forecast = pd.DataFrame(result["forecast"]).rename(columns={"predicted_sales": "sales"})
    history["series"] = "Actual"
    forecast["series"] = "Forecast"
    combined = pd.concat([history[["date", "sales", "series"]], forecast[["date", "sales", "series"]]], ignore_index=True)
    st.plotly_chart(px.line(combined, x="date", y="sales", color="series", markers=True, title="Sales forecast"), use_container_width=True)


def render_churn(result: dict) -> None:
    st.subheader("Customer churn")
    if not result.get("available"):
        unavailable_panel(result)
        return

    metrics = result["metrics"]
    cols = st.columns(4)
    cols[0].metric("Accuracy", f"{metrics['accuracy']:.2%}")
    cols[1].metric("Precision", f"{metrics['precision']:.2%}")
    cols[2].metric("Recall", f"{metrics['recall']:.2%}")
    cols[3].metric("F1", f"{metrics['f1']:.2%}")

    left, right = st.columns(2)
    with left:
        matrix = pd.DataFrame(result["confusion_matrix"], index=["Actual 0", "Actual 1"], columns=["Predicted 0", "Predicted 1"])
        st.plotly_chart(px.imshow(matrix, text_auto=True, title="Confusion matrix"), use_container_width=True)
    with right:
        roc = pd.DataFrame(result["roc_curve"])
        st.plotly_chart(px.line(roc, x="fpr", y="tpr", markers=True, title="ROC curve"), use_container_width=True)

    st.dataframe(pd.DataFrame(result["high_risk_customers"]), hide_index=True, use_container_width=True)


def render_segmentation(result: dict) -> None:
    st.subheader("Customer segmentation")
    if not result.get("available"):
        unavailable_panel(result)
        return

    cols = st.columns(2)
    cols[0].metric("Optimal clusters", result["optimal_clusters"])
    cols[1].metric("Silhouette score", f"{result['silhouette_score']:.3f}")

    left, right = st.columns(2)
    with left:
        elbow = pd.DataFrame(result["elbow"])
        st.plotly_chart(px.line(elbow, x="k", y="inertia", markers=True, title="Elbow method"), use_container_width=True)
    with right:
        summary = pd.DataFrame(result["segment_summary"])
        st.plotly_chart(px.bar(summary, x="segment", y="revenue", title="Segment revenue"), use_container_width=True)

    st.dataframe(pd.DataFrame(result["segments"]), hide_index=True, use_container_width=True)


def render_machine_learning(token: str) -> None:
    st.subheader("Machine learning")
    try:
        datasets = api.list_datasets(token)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not datasets:
        st.caption("Upload a dataset to train machine learning models.")
        return

    selected_id = st.selectbox(
        "Dataset",
        options=[dataset["id"] for dataset in datasets],
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["id"] == dataset_id),
        key="ml_dataset",
    )

    processing_key = f"ml_processing_{selected_id}"
    if st.button("Generate models", type="primary", disabled=st.session_state.get(processing_key, False)):
        st.session_state[processing_key] = True
        try:
            with st.spinner("Training forecasting, churn, and segmentation models..."):
                st.session_state["ml_result"] = api.generate_machine_learning(token, selected_id)
            st.session_state["ml_dataset_id"] = selected_id
        except api.ApiError as exc:
            st.error(str(exc))
            return
        finally:
            st.session_state[processing_key] = False

    result = st.session_state.get("ml_result")
    if not result or st.session_state.get("ml_dataset_id") != selected_id:
        st.caption("Generate models to view forecasts, churn risk, and customer segments.")
        return

    render_sales_forecast(result["sales_forecast"])
    render_churn(result["customer_churn"])
    render_segmentation(result["customer_segmentation"])
