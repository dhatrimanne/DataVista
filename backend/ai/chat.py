from __future__ import annotations

from typing import Any

import pandas as pd

from backend.ai.gemini import GeminiClient, InsightClient, compact_json
from backend.analytics.eda import records


def build_chat_context(dataset: dict, analysis: dict[str, Any], dataframe: pd.DataFrame) -> dict[str, Any]:
    return {
        "dataset": {
            "name": dataset["name"],
            "rows": dataset["row_count"],
            "columns": dataset["column_count"],
            "data_quality_score": dataset["data_quality_score"],
        },
        "analytics": analysis,
        "sample_rows": records(dataframe, limit=20),
        "columns": list(dataframe.columns),
    }


def build_chat_prompt(question: str, context: dict[str, Any]) -> str:
    return (
        "You are DataVista's dataset chat assistant.\n"
        "Answer only from the supplied dataset context, analytics, and sample rows. "
        "Do not use outside knowledge or invent facts. If the context cannot answer the question, say what data is missing. "
        "Be concise and cite the metric, column, or analytics section used.\n\n"
        f"Question: {question}\n\n"
        "Dataset context:\n"
        f"{compact_json(context)}"
    )


def answer_dataset_question(
    question: str,
    dataset: dict,
    analysis: dict[str, Any],
    dataframe: pd.DataFrame,
    client: InsightClient | None = None,
) -> dict[str, Any]:
    context = build_chat_context(dataset, analysis, dataframe)
    prompt = build_chat_prompt(question, context)
    answer = (client or GeminiClient()).generate(prompt)
    return {
        "answer": answer,
        "dataset_name": dataset["name"],
        "used_columns": context["columns"],
    }
