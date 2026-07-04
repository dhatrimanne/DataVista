from backend.ai.chat import answer_dataset_question, build_chat_prompt
from tests.test_ai_insights import analysis_payload, register_user


class FakeClient:
    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return "Product A leads revenue based on product_analysis.best_sellers."


def upload_chat_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Product,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,100,20\n"
        b"2026-02-01,2,C2,A,120,25\n"
        b"2026-03-01,3,C3,B,80,10\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("chat.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_chat_prompt_restricts_answer_to_dataset_context():
    prompt = build_chat_prompt("Which product performs best?", {"analytics": analysis_payload()})

    assert "Answer only from the supplied dataset context" in prompt
    assert "Do not use outside knowledge" in prompt
    assert "Which product performs best?" in prompt


def test_dataset_question_uses_injected_client():
    import pandas as pd

    fake = FakeClient()
    response = answer_dataset_question(
        "Which product performs best?",
        {"name": "Retail", "row_count": 3, "column_count": 2, "data_quality_score": 95},
        analysis_payload(),
        pd.DataFrame({"product": ["A"], "revenue": [100]}),
        client=fake,
    )

    assert "Product A" in response["answer"]
    assert "Retail" in fake.prompt
    assert response["used_columns"] == ["product", "revenue"]


def test_ai_chat_api_is_validated_and_user_scoped(client, monkeypatch):
    owner_token = register_user(client, "chat-owner@example.com")
    other_token = register_user(client, "chat-other@example.com")
    dataset_id = upload_chat_dataset(client, owner_token)

    def fake_answer(question, dataset, analysis, dataframe):
        return {"answer": "Product A leads revenue.", "dataset_name": dataset["name"], "used_columns": list(dataframe.columns)}

    monkeypatch.setattr("backend.routes.datasets.answer_dataset_question", fake_answer)

    response = client.post(
        f"/datasets/{dataset_id}/chat",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"question": "Which product performs best?"},
    )
    invalid_response = client.post(
        f"/datasets/{dataset_id}/chat",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"question": "x"},
    )
    forbidden_response = client.post(
        f"/datasets/{dataset_id}/chat",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"question": "Which product performs best?"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Product A leads revenue."
    assert invalid_response.status_code == 422
    assert forbidden_response.status_code == 404
