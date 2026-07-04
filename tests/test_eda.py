import pandas as pd

from backend.analytics.eda import analyze_dataframe


def test_eda_generates_supported_business_sections():
    dataframe = pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-10"],
            "order_id": [1, 2, 3, 4],
            "customer_id": ["C1", "C1", "C2", "C3"],
            "product": ["A", "B", "A", "C"],
            "region": ["North", "North", "South", "West"],
            "revenue": [100.0, 200.0, 150.0, 50.0],
            "profit": [20.0, 50.0, 30.0, 5.0],
        }
    )

    analysis = analyze_dataframe(dataframe)

    assert analysis["kpis"]["revenue"] == 500.0
    assert analysis["kpis"]["profit"] == 105.0
    assert analysis["kpis"]["orders"] == 4
    assert analysis["customer_analysis"]["repeat_customers"] == 1
    assert analysis["product_analysis"]["best_sellers"][0]["product"] == "A"
    assert analysis["regional_analysis"]["performance"][0]["region"] == "North"
    assert len(analysis["time_analysis"]["monthly"]) == 2
    assert analysis["statistical_analysis"]["correlation"]


def test_eda_reports_unsupported_sections_without_inventing_metrics():
    dataframe = pd.DataFrame({"name": ["A", "B"], "note": ["x", "y"]})

    analysis = analyze_dataframe(dataframe)

    assert analysis["kpis"] == {}
    assert "sales" in analysis["unavailable_sections"]
    assert "customer" in analysis["unavailable_sections"]
    assert "product" in analysis["unavailable_sections"]
    assert analysis["customer_analysis"] == {}
    assert analysis["regional_analysis"] == {}


def register_user(client, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "EDA User", "password": "StrongPass123"},
    )
    return response.json()["access_token"]


def upload_business_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,100,20\n"
        b"2026-01-15,2,C1,B,North,200,50\n"
        b"2026-02-01,3,C2,A,South,150,30\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("business.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_analysis_api_is_persisted_regenerable_and_user_scoped(client):
    owner_token = register_user(client, "eda-owner@example.com")
    other_token = register_user(client, "eda-other@example.com")
    dataset_id = upload_business_dataset(client, owner_token)

    get_response = client.get(
        f"/datasets/{dataset_id}/analysis",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    regenerate_response = client.post(
        f"/datasets/{dataset_id}/analysis",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_response = client.get(
        f"/datasets/{dataset_id}/analysis",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["kpis"]["revenue"] == 450.0
    assert regenerate_response.status_code == 200
    assert forbidden_response.status_code == 404
