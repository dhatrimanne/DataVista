from backend.ai.insights import build_insight_prompt, generate_business_insights
from backend.ai.gemini import GeminiClient


def dataset_metadata() -> dict:
    return {
        "id": 1,
        "name": "Retail",
        "row_count": 10,
        "column_count": 5,
        "missing_value_count": 0,
        "data_quality_score": 98,
        "cleaning_report": {"steps": ["normalized columns"]},
    }


def analysis_payload() -> dict:
    return {
        "detected_roles": {"revenue": "revenue"},
        "kpis": {"revenue": 1000, "profit": 200},
        "customer_analysis": {},
        "product_analysis": {"best_sellers": [{"product": "A", "revenue": 700}]},
        "regional_analysis": {},
        "time_analysis": {},
        "statistical_analysis": {},
        "supported_sections": ["sales", "product"],
        "unavailable_sections": ["customer"],
    }


def ml_payload() -> dict:
    return {
        "sales_forecast": {"available": True, "forecast": [{"date": "2026-09-01", "predicted_sales": 300}]},
        "customer_churn": {"available": False, "reason": "Missing churn labels."},
        "customer_segmentation": {"available": False, "reason": "Missing customer identifiers."},
    }


class FakeClient:
    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return "## Executive Summary\nRevenue is 1000 based on supplied KPIs."


def register_user(client, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "AI User", "password": "StrongPass123"},
    )
    return response.json()["access_token"]


def upload_ai_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Product,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,100,20\n"
        b"2026-02-01,2,C2,A,120,25\n"
        b"2026-03-01,3,C3,B,140,30\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("ai.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_ai_insight_prompt_restricts_generation_to_supplied_context():
    prompt = build_insight_prompt({"analytics": analysis_payload()})

    assert "Use only the supplied JSON context" in prompt
    assert "Do not invent unsupported facts" in prompt
    assert "Next Quarter Strategy" in prompt


def test_generate_business_insights_uses_injected_client():
    fake = FakeClient()
    result = generate_business_insights(dataset_metadata(), analysis_payload(), ml_payload(), client=fake)

    assert "Revenue is 1000" in result["insights"]
    assert "Retail" in fake.prompt
    assert result["context_summary"]["ml_available"]["sales_forecast"] is True


def test_ai_insights_api_records_usage_and_is_user_scoped(client, monkeypatch):
    owner_token = register_user(client, "ai-owner@example.com")
    other_token = register_user(client, "ai-other@example.com")
    dataset_id = upload_ai_dataset(client, owner_token)

    def fake_generate(dataset, analysis, ml_results):
        return {
            "insights": "## Executive Summary\nRevenue is supported by KPIs.",
            "sections": ["Executive Summary"],
            "context_summary": {
                "dataset_name": dataset["name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
                "analysis_sections": analysis["supported_sections"],
                "ml_available": {
                    "sales_forecast": ml_results["sales_forecast"]["available"],
                    "customer_churn": ml_results["customer_churn"]["available"],
                    "customer_segmentation": ml_results["customer_segmentation"]["available"],
                },
            },
        }

    monkeypatch.setattr("backend.routes.datasets.generate_business_insights", fake_generate)

    response = client.post(
        f"/datasets/{dataset_id}/insights",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_response = client.post(
        f"/datasets/{dataset_id}/insights",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    dashboard_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {owner_token}"})

    assert response.status_code == 200
    assert "Executive Summary" in response.json()["insights"]
    assert forbidden_response.status_code == 404
    assert dashboard_response.json()["ai_insights_generated"] == 1


def test_gemini_client_explains_missing_configuration(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv("GEMINI_API_KEY", "")
    from backend.config import get_settings

    get_settings.cache_clear()

    try:
        GeminiClient().generate("hello")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "GEMINI_API_KEY" in exc.detail
    else:
        raise AssertionError("GeminiClient should require configuration.")
    finally:
        get_settings.cache_clear()


def test_gemini_client_uses_configured_api_key(monkeypatch):
    from backend.config import get_settings

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "Grounded answer"}]}}]}

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr("backend.ai.gemini.requests.post", fake_post)
    get_settings.cache_clear()

    result = GeminiClient().generate("Use supplied context only.")

    assert result == "Grounded answer"
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["url"].endswith("/v1beta/models/gemini-test:generateContent")
    assert captured["json"]["contents"][0]["parts"][0]["text"] == "Use supplied context only."
    get_settings.cache_clear()
