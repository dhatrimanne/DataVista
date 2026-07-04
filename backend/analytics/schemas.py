from typing import Any

from pydantic import BaseModel, Field


class DatasetAnalysis(BaseModel):
    detected_roles: dict[str, str]
    kpis: dict[str, Any]
    customer_analysis: dict[str, Any]
    product_analysis: dict[str, Any]
    regional_analysis: dict[str, Any]
    time_analysis: dict[str, Any]
    statistical_analysis: dict[str, Any]
    supported_sections: list[str]
    unavailable_sections: list[str]
    created_at: str | None = None
    updated_at: str | None = None


class InteractiveDashboard(BaseModel):
    detected_roles: dict[str, str]
    filters: dict[str, Any]
    active_filters: dict[str, Any]
    kpis: dict[str, Any]
    trend: list[dict[str, Any]]
    category_breakdown: list[dict[str, Any]]
    subcategory_breakdown: list[dict[str, Any]]
    region_breakdown: list[dict[str, Any]]
    state_breakdown: list[dict[str, Any]]
    product_breakdown: list[dict[str, Any]]
    customer_segment_breakdown: list[dict[str, Any]]
    scatter: list[dict[str, Any]]
    treemap: list[dict[str, Any]]
    bubble: list[dict[str, Any]]
    correlation_heatmap: list[dict[str, Any]]
    record_count: int


class MachineLearningResult(BaseModel):
    sales_forecast: dict[str, Any]
    customer_churn: dict[str, Any]
    customer_segmentation: dict[str, Any]


class BusinessInsights(BaseModel):
    insights: str
    sections: list[str]
    context_summary: dict[str, Any]


class DatasetChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class DatasetChatResponse(BaseModel):
    answer: str
    dataset_name: str
    used_columns: list[str]


class RecommendationResult(BaseModel):
    recommendations: list[dict[str, Any]]
    summary: dict[str, Any]
