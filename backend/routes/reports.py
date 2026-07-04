from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.ai.insights import generate_business_insights
from backend.analytics.recommendations import build_recommendations
from backend.analytics.repository import get_analysis
from backend.auth.dependencies import get_current_user
from backend.dashboard.repository import record_activity
from backend.datasets.repository import get_dataset
from backend.datasets.service import dataset_cleaned_path, generate_dataset_analysis
from backend.ml.models import build_customer_churn, build_customer_segmentation, build_sales_forecast
from backend.reports.generator import generate_pdf_report, report_path
from backend.reports.repository import create_report, delete_report, get_report, list_reports
from backend.reports.schemas import ReportCreate, ReportCreateResponse, ReportList
from backend.utils.dataframe_cache import read_csv_cached
from backend.utils.logging import get_logger


router = APIRouter(prefix="/reports", tags=["Reports"])
logger = get_logger()


def public_report(report: dict) -> dict:
    return {
        "id": report["id"],
        "user_id": report["user_id"],
        "dataset_id": report["dataset_id"],
        "title": report["title"],
        "filename": report["filename"],
        "file_size_bytes": report["file_size_bytes"],
        "created_at": report["created_at"],
    }


@router.get("", response_model=ReportList)
def get_reports(current_user: dict = Depends(get_current_user)) -> dict:
    return {"reports": [public_report(report) for report in list_reports(current_user["id"])]}


@router.post("", response_model=ReportCreateResponse, status_code=status.HTTP_201_CREATED)
def create_pdf_report(payload: ReportCreate, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(payload.dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    dataframe = read_csv_cached(dataset_cleaned_path(payload.dataset_id, current_user["id"]))
    analysis = get_analysis(payload.dataset_id, current_user["id"])
    if analysis is None:
        analysis = generate_dataset_analysis(payload.dataset_id, current_user["id"])
    recommendations = build_recommendations(analysis)
    ml_results = {
        "sales_forecast": build_sales_forecast(dataframe),
        "customer_churn": build_customer_churn(dataframe),
        "customer_segmentation": build_customer_segmentation(dataframe),
    }
    insights = None
    if payload.include_ai_insights:
        try:
            insights = generate_business_insights(dataset, analysis, ml_results)["insights"]
        except HTTPException as exc:
            if exc.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
                raise
            insights = "Gemini AI insights are not configured. Set GEMINI_API_KEY in .env to include AI executive summaries."

    filename, path = generate_pdf_report(current_user["id"], dataset, analysis, recommendations, ml_results, insights)
    report = create_report(
        current_user["id"],
        payload.dataset_id,
        f"{dataset['name']} Business Report",
        filename,
        path.stat().st_size,
    )
    logger.info("report_generated user_id=%s dataset_id=%s report_id=%s", current_user["id"], payload.dataset_id, report["id"])
    record_activity(current_user["id"], "report_generated", f"Generated report for {dataset['name']}.")
    return {"report": public_report(report)}


@router.get("/{report_id}/download")
def download_report(report_id: int, current_user: dict = Depends(get_current_user)) -> FileResponse:
    report = get_report(report_id, current_user["id"])
    if report is None or not report["filename"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    try:
        path = report_path(current_user["id"], report["filename"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file is missing.") from exc
    return FileResponse(path, media_type="application/pdf", filename=f"{Path(report['title']).stem}.pdf")


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_report(report_id: int, current_user: dict = Depends(get_current_user)) -> None:
    report = get_report(report_id, current_user["id"])
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if report["filename"]:
        try:
            report_path(current_user["id"], report["filename"]).unlink(missing_ok=True)
        except FileNotFoundError:
            pass
    if delete_report(report_id, current_user["id"]):
        logger.info("report_deleted user_id=%s report_id=%s", current_user["id"], report_id)
        record_activity(current_user["id"], "report_deleted", f"Deleted report {report['title']}.")
