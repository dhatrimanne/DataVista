from __future__ import annotations

from typing import Any

from backend.ai.gemini import GeminiClient, InsightClient, compact_json


INSIGHT_SECTIONS = [
    "Executive Summary",
    "Key Findings",
    "Opportunities",
    "Risks",
    "Weak Areas",
    "Growth Suggestions",
    "Marketing Recommendations",
    "Inventory Recommendations",
    "Pricing Recommendations",
    "Customer Recommendations",
    "Next Quarter Strategy",
]


def build_insight_context(
    dataset: dict,
    analysis: dict[str, Any],
    ml_results: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset": {
            "name": dataset["name"],
            "rows": dataset["row_count"],
            "columns": dataset["column_count"],
            "missing_values": dataset["missing_value_count"],
            "data_quality_score": dataset["data_quality_score"],
            "cleaning_report": dataset["cleaning_report"],
        },
        "analytics": analysis,
        "machine_learning": ml_results,
    }


def build_insight_prompt(context: dict[str, Any]) -> str:
    sections = "\n".join(f"- {section}" for section in INSIGHT_SECTIONS)
    return (
        "You are DataVista's business analytics assistant.\n"
        "Use only the supplied JSON context. Do not invent unsupported facts, causes, customers, products, regions, "
        "or trends. If evidence is missing, say exactly what data is missing.\n"
        "Return concise Markdown with these sections:\n"
        f"{sections}\n\n"
        "Every recommendation must cite the specific metric or analytics section it is based on.\n"
        "JSON context:\n"
        f"{compact_json(context)}"
    )


def generate_business_insights(
    dataset: dict,
    analysis: dict[str, Any],
    ml_results: dict[str, Any],
    client: InsightClient | None = None,
) -> dict[str, Any]:
    context = build_insight_context(dataset, analysis, ml_results)
    prompt = build_insight_prompt(context)
    text = (client or GeminiClient()).generate(prompt)
    return {
        "insights": text,
        "sections": INSIGHT_SECTIONS,
        "context_summary": {
            "dataset_name": dataset["name"],
            "rows": dataset["row_count"],
            "columns": dataset["column_count"],
            "analysis_sections": analysis.get("supported_sections", []),
            "ml_available": {
                "sales_forecast": bool(ml_results["sales_forecast"].get("available")),
                "customer_churn": bool(ml_results["customer_churn"].get("available")),
                "customer_segmentation": bool(ml_results["customer_segmentation"].get("available")),
            },
        },
    }
