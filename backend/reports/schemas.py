from pydantic import BaseModel


class ReportCreate(BaseModel):
    dataset_id: int
    include_ai_insights: bool = False


class ReportSummary(BaseModel):
    id: int
    user_id: int
    dataset_id: int | None
    title: str
    filename: str | None
    file_size_bytes: int
    created_at: str


class ReportList(BaseModel):
    reports: list[ReportSummary]


class ReportCreateResponse(BaseModel):
    report: ReportSummary
