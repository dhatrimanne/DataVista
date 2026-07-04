from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from backend.ai.chat import answer_dataset_question
from backend.ai.insights import generate_business_insights
from backend.ai.repository import record_ai_insight
from backend.auth.dependencies import get_current_user
from backend.analytics.interactive_dashboard import DashboardFilters, build_interactive_dashboard
from backend.analytics.recommendations import build_recommendations
from backend.analytics.repository import get_analysis
from backend.analytics.schemas import (
    BusinessInsights,
    DatasetAnalysis,
    DatasetChatRequest,
    DatasetChatResponse,
    InteractiveDashboard,
    MachineLearningResult,
    RecommendationResult,
)
from backend.dashboard.repository import record_activity
from backend.datasets.repository import (
    create_dataset,
    delete_dataset,
    get_dataset,
    list_dataset_history,
    list_datasets,
    mark_reanalyzed,
    public_dataset,
    rename_dataset,
)
from backend.datasets.schemas import DatasetDetail, DatasetList, DatasetRename, DatasetSummary
from backend.datasets.service import (
    clean_existing_dataset,
    dataset_cleaned_path,
    generate_dataset_analysis,
    persist_upload,
    remove_dataset_files,
)
from backend.ml.models import build_customer_churn, build_customer_segmentation, build_sales_forecast
from backend.ml.repository import record_forecast
from backend.utils.dataframe_cache import read_csv_cached
from backend.utils.logging import get_logger


router = APIRouter(prefix="/datasets", tags=["Datasets"])
logger = get_logger()


@router.post("", response_model=DatasetSummary, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    remove_outliers: bool = Query(False),
    current_user: dict = Depends(get_current_user),
) -> dict:
    metadata = await persist_upload(file, current_user["id"], remove_outliers=remove_outliers)
    try:
        dataset = create_dataset(current_user["id"], metadata)
    except ValueError as exc:
        remove_dataset_files({"user_id": current_user["id"], **metadata})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    logger.info("dataset_uploaded user_id=%s dataset_id=%s filename=%s", current_user["id"], dataset["id"], dataset["original_filename"])
    generate_dataset_analysis(dataset["id"], current_user["id"])
    record_activity(current_user["id"], "dataset_uploaded", f"Uploaded dataset {dataset['name']}.")
    record_activity(current_user["id"], "cleaning_completed", f"Cleaned dataset {dataset['name']}.")
    record_activity(current_user["id"], "analysis_completed", f"Analyzed dataset {dataset['name']}.")
    return public_dataset(dataset)


@router.get("", response_model=DatasetList)
def get_datasets(current_user: dict = Depends(get_current_user)) -> dict:
    return {"datasets": [public_dataset(dataset) for dataset in list_datasets(current_user["id"])]}


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset_detail(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return {
        **public_dataset(dataset),
        "history": list_dataset_history(dataset_id, current_user["id"]),
        "cleaning_report": dataset["cleaning_report"],
    }


@router.patch("/{dataset_id}", response_model=DatasetSummary)
def update_dataset_name(
    dataset_id: int,
    payload: DatasetRename,
    current_user: dict = Depends(get_current_user),
) -> dict:
    dataset = rename_dataset(dataset_id, current_user["id"], payload.name)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    record_activity(current_user["id"], "dataset_renamed", f"Renamed dataset to {dataset['name']}.")
    return public_dataset(dataset)


@router.post("/{dataset_id}/reanalyze", response_model=DatasetSummary)
def reanalyze_dataset(
    dataset_id: int,
    remove_outliers: bool = Query(False),
    current_user: dict = Depends(get_current_user),
) -> dict:
    metadata = clean_existing_dataset(dataset_id, current_user["id"], remove_outliers=remove_outliers)
    dataset = mark_reanalyzed(dataset_id, current_user["id"], metadata)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    generate_dataset_analysis(dataset_id, current_user["id"])
    record_activity(current_user["id"], "dataset_reanalyzed", f"Re-analyzed dataset {dataset['name']}.")
    record_activity(current_user["id"], "cleaning_completed", f"Cleaned dataset {dataset['name']}.")
    record_activity(current_user["id"], "analysis_completed", f"Analyzed dataset {dataset['name']}.")
    return public_dataset(dataset)


@router.get("/{dataset_id}/analysis", response_model=DatasetAnalysis)
def get_dataset_analysis(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    analysis = get_analysis(dataset_id, current_user["id"])
    if analysis is None:
        analysis = generate_dataset_analysis(dataset_id, current_user["id"])
    return analysis


@router.post("/{dataset_id}/analysis", response_model=DatasetAnalysis)
def regenerate_dataset_analysis(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    analysis = generate_dataset_analysis(dataset_id, current_user["id"])
    record_activity(current_user["id"], "analysis_generated", f"Generated analysis for {dataset['name']}.")
    record_activity(current_user["id"], "analysis_completed", f"Analyzed dataset {dataset['name']}.")
    return analysis


@router.get("/{dataset_id}/dashboard-data", response_model=InteractiveDashboard)
def get_interactive_dashboard(
    dataset_id: int,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    year: int | None = Query(None, ge=1900, le=2200),
    month: int | None = Query(None, ge=1, le=12),
    category: str | None = Query(None),
    subcategory: str | None = Query(None),
    region: str | None = Query(None),
    state: str | None = Query(None),
    customer_segment: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    dataframe = read_csv_cached(dataset_cleaned_path(dataset_id, current_user["id"]))
    filters = DashboardFilters(
        start_date=start_date,
        end_date=end_date,
        year=year,
        month=month,
        category=category,
        subcategory=subcategory,
        region=region,
        state=state,
        customer_segment=customer_segment,
    )
    return build_interactive_dashboard(dataframe, filters)


@router.post("/{dataset_id}/ml", response_model=MachineLearningResult)
def generate_machine_learning(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    dataframe = read_csv_cached(dataset_cleaned_path(dataset_id, current_user["id"]))
    sales_forecast = build_sales_forecast(dataframe)
    if sales_forecast.get("available"):
        record_forecast(current_user["id"], dataset_id, sales_forecast["model"])
        logger.info("forecast_generated user_id=%s dataset_id=%s model=%s", current_user["id"], dataset_id, sales_forecast["model"])
        record_activity(current_user["id"], "forecast_generated", f"Generated forecast for {dataset['name']}.")

    return {
        "sales_forecast": sales_forecast,
        "customer_churn": build_customer_churn(dataframe),
        "customer_segmentation": build_customer_segmentation(dataframe),
    }


@router.post("/{dataset_id}/insights", response_model=BusinessInsights)
def generate_insights(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    dataframe = read_csv_cached(dataset_cleaned_path(dataset_id, current_user["id"]))
    analysis = get_analysis(dataset_id, current_user["id"])
    if analysis is None:
        analysis = generate_dataset_analysis(dataset_id, current_user["id"])
    ml_results = {
        "sales_forecast": build_sales_forecast(dataframe),
        "customer_churn": build_customer_churn(dataframe),
        "customer_segmentation": build_customer_segmentation(dataframe),
    }
    insights = generate_business_insights(dataset, analysis, ml_results)
    logger.info("ai_insights_generated user_id=%s dataset_id=%s", current_user["id"], dataset_id)
    record_ai_insight(current_user["id"], dataset_id)
    record_activity(current_user["id"], "ai_insights_generated", f"Generated AI insights for {dataset['name']}.")
    return insights


@router.post("/{dataset_id}/chat", response_model=DatasetChatResponse)
def chat_with_dataset(
    dataset_id: int,
    payload: DatasetChatRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    dataframe = read_csv_cached(dataset_cleaned_path(dataset_id, current_user["id"]))
    analysis = get_analysis(dataset_id, current_user["id"])
    if analysis is None:
        analysis = generate_dataset_analysis(dataset_id, current_user["id"])
    answer = answer_dataset_question(payload.question, dataset, analysis, dataframe)
    logger.info("ai_chat_answered user_id=%s dataset_id=%s", current_user["id"], dataset_id)
    record_activity(current_user["id"], "ai_chat_answered", f"Answered a question about {dataset['name']}.")
    return answer


@router.get("/{dataset_id}/recommendations", response_model=RecommendationResult)
def get_recommendations(dataset_id: int, current_user: dict = Depends(get_current_user)) -> dict:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    analysis = get_analysis(dataset_id, current_user["id"])
    if analysis is None:
        analysis = generate_dataset_analysis(dataset_id, current_user["id"])
    return build_recommendations(analysis)


@router.get("/{dataset_id}/download-cleaned")
def download_cleaned_dataset(dataset_id: int, current_user: dict = Depends(get_current_user)) -> FileResponse:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    path = dataset_cleaned_path(dataset_id, current_user["id"])
    download_name = f"{dataset['name']}_cleaned.csv"
    return FileResponse(path, media_type="text/csv", filename=download_name)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dataset(dataset_id: int, current_user: dict = Depends(get_current_user)) -> None:
    dataset = get_dataset(dataset_id, current_user["id"])
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    remove_dataset_files(dataset)
    deleted = delete_dataset(dataset_id, current_user["id"])
    if deleted:
        record_activity(current_user["id"], "dataset_deleted", f"Deleted dataset {dataset['name']}.")
