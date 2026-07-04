from pathlib import Path
from hashlib import sha256
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from backend.analytics.cleaning import clean_dataframe
from backend.analytics.eda import analyze_dataframe
from backend.analytics.repository import save_analysis
from backend.config import get_settings, resolve_app_path
from backend.datasets.repository import get_dataset
from backend.datasets.repository import get_dataset_by_hash
from backend.utils.dataframe_cache import read_csv_cached


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "latin1", "cp1252")
ALLOWED_CONTENT_TYPES = {
    "csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "xls": {"application/vnd.ms-excel", "application/octet-stream"},
}


def validate_filename(filename: str) -> tuple[str, str]:
    safe_name = Path(filename).name
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and Excel files are supported.",
        )
    return safe_name, extension.removeprefix(".")


def user_storage_dir(base_dir: str, user_id: int) -> Path:
    return resolve_app_path(base_dir) / str(user_id)


def read_dataset(path: Path, file_type: str) -> pd.DataFrame:
    if file_type == "csv":
        failures: list[Exception] = []
        for encoding in CSV_ENCODINGS:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError as exc:
                failures.append(exc)
        raise ValueError("CSV file could not be decoded with supported encodings.") from failures[-1]
    return pd.read_excel(path)


def dataframe_metadata(dataframe: pd.DataFrame, cleaning_report: dict | None = None) -> dict:
    return {
        "row_count": int(dataframe.shape[0]),
        "column_count": int(dataframe.shape[1]),
        "missing_value_count": int(dataframe.isna().sum().sum()),
        "data_quality_score": cleaning_report.get("data_quality_score") if cleaning_report else None,
        "cleaning_report": cleaning_report,
    }


def write_cleaned_dataset(dataframe: pd.DataFrame, cleaned_path: Path) -> None:
    export = dataframe.copy()
    for column in export.columns:
        if pd.api.types.is_datetime64_any_dtype(export[column]):
            export[column] = export[column].dt.strftime("%Y-%m-%d")
    export.to_csv(cleaned_path, index=False)


def clean_and_store(dataframe: pd.DataFrame, cleaned_path: Path, remove_outliers: bool = False) -> dict:
    result = clean_dataframe(dataframe, remove_outliers=remove_outliers)
    write_cleaned_dataset(result.dataframe, cleaned_path)
    return dataframe_metadata(result.dataframe, result.report)


async def persist_upload(file: UploadFile, user_id: int, remove_outliers: bool = False) -> dict:
    settings = get_settings()
    original_filename, file_type = validate_filename(file.filename or "")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB upload limit.",
        )
    allowed_types = ALLOWED_CONTENT_TYPES.get(file_type, set())
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file content type does not match the file extension.",
        )
    content_hash = sha256(content).hexdigest()
    if get_dataset_by_hash(user_id, content_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dataset has already been uploaded to your workspace.",
        )

    upload_dir = user_storage_dir(settings.upload_dir, user_id)
    cleaned_dir = user_storage_dir(settings.cleaned_data_dir, user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid4().hex}.{file_type}"
    stored_path = upload_dir / unique_name
    stored_path.write_bytes(content)

    try:
        dataframe = read_dataset(stored_path, file_type)
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file could not be parsed as a valid dataset.",
        ) from exc

    cleaned_filename = f"{stored_path.stem}.csv"
    cleaned_path = cleaned_dir / cleaned_filename
    metadata = clean_and_store(dataframe, cleaned_path, remove_outliers=remove_outliers)

    return {
        "name": Path(original_filename).stem,
        "original_filename": original_filename,
        "stored_filename": unique_name,
        "cleaned_filename": cleaned_filename,
        "content_hash": content_hash,
        "file_type": file_type,
        "file_size_bytes": len(content),
        "status": "analyzed",
        **metadata,
    }


def clean_existing_dataset(dataset_id: int, user_id: int, remove_outliers: bool = False) -> dict:
    original_path, file_type = dataset_original_path(dataset_id, user_id)
    dataframe = read_dataset(original_path, file_type)
    cleaned_path = dataset_cleaned_path(dataset_id, user_id)
    return clean_and_store(dataframe, cleaned_path, remove_outliers=remove_outliers)


def generate_dataset_analysis(dataset_id: int, user_id: int) -> dict:
    cleaned_path = dataset_cleaned_path(dataset_id, user_id)
    dataframe = read_csv_cached(cleaned_path)
    analysis = analyze_dataframe(dataframe)
    save_analysis(dataset_id, user_id, analysis)
    return analysis


def dataset_cleaned_path(dataset_id: int, user_id: int) -> Path:
    dataset = get_dataset(dataset_id, user_id)
    if dataset is None or not dataset["cleaned_filename"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    path = user_storage_dir(get_settings().cleaned_data_dir, user_id) / dataset["cleaned_filename"]
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cleaned dataset file is missing.")
    return path


def dataset_original_path(dataset_id: int, user_id: int) -> tuple[Path, str]:
    dataset = get_dataset(dataset_id, user_id)
    if dataset is None or not dataset["stored_filename"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    path = user_storage_dir(get_settings().upload_dir, user_id) / dataset["stored_filename"]
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original dataset file is missing.")
    return path, dataset["file_type"]


def remove_dataset_files(dataset: dict) -> None:
    settings = get_settings()
    if dataset.get("stored_filename"):
        (user_storage_dir(settings.upload_dir, dataset["user_id"]) / dataset["stored_filename"]).unlink(missing_ok=True)
    if dataset.get("cleaned_filename"):
        (user_storage_dir(settings.cleaned_data_dir, dataset["user_id"]) / dataset["cleaned_filename"]).unlink(
            missing_ok=True
        )
