import pandas as pd

from backend.ml.models import build_customer_churn, build_customer_segmentation, build_sales_forecast


def ml_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": [
                "2026-01-01",
                "2026-02-01",
                "2026-03-01",
                "2026-04-01",
                "2026-05-01",
                "2026-06-01",
                "2026-07-01",
                "2026-08-01",
            ],
            "order_id": [1, 2, 3, 4, 5, 6, 7, 8],
            "customer_id": ["C1", "C2", "C3", "C4", "C5", "C6", "C1", "C2"],
            "revenue": [100, 120, 140, 160, 190, 210, 240, 260],
            "profit": [20, 22, 25, 30, 36, 40, 44, 48],
            "quantity": [1, 1, 2, 2, 3, 3, 4, 4],
            "churn": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )


def register_user(client, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "ML User", "password": "StrongPass123"},
    )
    return response.json()["access_token"]


def upload_ml_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Revenue,Profit,Quantity,Churn\n"
        b"2026-01-01,1,C1,100,20,1,0\n"
        b"2026-02-01,2,C2,120,22,1,1\n"
        b"2026-03-01,3,C3,140,25,2,0\n"
        b"2026-04-01,4,C4,160,30,2,1\n"
        b"2026-05-01,5,C5,190,36,3,0\n"
        b"2026-06-01,6,C6,210,40,3,1\n"
        b"2026-07-01,7,C1,240,44,4,0\n"
        b"2026-08-01,8,C2,260,48,4,1\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("ml.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_machine_learning_models_generate_expected_outputs():
    dataframe = ml_dataframe()

    forecast = build_sales_forecast(dataframe)
    churn = build_customer_churn(dataframe)
    segmentation = build_customer_segmentation(dataframe)

    assert forecast["available"] is True
    assert len(forecast["forecast"]) == 3
    assert {"rmse", "mae", "r2"} <= forecast["metrics"].keys()
    assert churn["available"] is True
    assert len(churn["confusion_matrix"]) == 2
    assert segmentation["available"] is True
    assert segmentation["optimal_clusters"] >= 2
    assert segmentation["segments"]


def test_churn_explains_missing_label_requirements():
    result = build_customer_churn(pd.DataFrame({"revenue": [1, 2, 3], "profit": [1, 1, 1]}))

    assert result["available"] is False
    assert "churn" in result["required_data"][0]


def test_machine_learning_api_records_forecast_and_is_user_scoped(client):
    owner_token = register_user(client, "ml-owner@example.com")
    other_token = register_user(client, "ml-other@example.com")
    dataset_id = upload_ml_dataset(client, owner_token)

    response = client.post(
        f"/datasets/{dataset_id}/ml",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_response = client.post(
        f"/datasets/{dataset_id}/ml",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    dashboard_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {owner_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["sales_forecast"]["available"] is True
    assert body["customer_churn"]["available"] is True
    assert body["customer_segmentation"]["available"] is True
    assert forbidden_response.status_code == 404
    assert dashboard_response.json()["forecasts_generated"] == 1
