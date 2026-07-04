from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    row_count: int
    column_count: int
    missing_value_count: int
    data_quality_score: int | None = None
    status: str
    created_at: str
    updated_at: str


class DatasetRename(BaseModel):
    name: str = Field(min_length=1, max_length=140)


class DatasetHistoryEvent(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: str


class DatasetDetail(DatasetSummary):
    history: list[DatasetHistoryEvent]
    cleaning_report: dict | None = None


class DatasetList(BaseModel):
    datasets: list[DatasetSummary]
