from backend.analytics.recommendations import build_recommendations
from tests.test_ai_insights import register_user


def recommendation_analysis() -> dict:
    return {
        "detected_roles": {"revenue": "revenue", "profit": "profit", "product": "product", "region": "region"},
        "product_analysis": {
            "best_sellers": [{"product": "A", "revenue": 500}, {"product": "B", "revenue": 300}],
            "worst_sellers": [{"product": "C", "revenue": 50}],
            "most_profitable": [{"product": "A", "profit": 180}],
            "least_profitable": [{"product": "C", "profit": 5}],
        },
        "regional_analysis": {"performance": [{"region": "North", "revenue": 700}, {"region": "West", "revenue": 80}]},
        "customer_analysis": {
            "top_customers": [{"customer_id": "C1", "revenue": 800}],
            "rfm": [{"customer_id": "C2", "recency": 90, "frequency": 1, "monetary": 100}],
        },
    }


def upload_recommendation_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,500,180\n"
        b"2026-01-02,2,C2,B,North,300,90\n"
        b"2026-01-03,3,C3,C,West,50,5\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("recommendations.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_recommendation_engine_generates_core_categories():
    result = build_recommendations(recommendation_analysis())
    categories = {item["category"] for item in result["recommendations"]}

    assert "Products to promote" in categories
    assert "Regions needing attention" in categories
    assert "Cross-selling opportunities" in categories
    assert result["summary"]["total"] == len(result["recommendations"])


def test_recommendations_api_is_user_scoped(client):
    owner_token = register_user(client, "recommend-owner@example.com")
    other_token = register_user(client, "recommend-other@example.com")
    dataset_id = upload_recommendation_dataset(client, owner_token)

    response = client.get(
        f"/datasets/{dataset_id}/recommendations",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_response = client.get(
        f"/datasets/{dataset_id}/recommendations",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200
    assert response.json()["summary"]["total"] > 0
    assert forbidden_response.status_code == 404
