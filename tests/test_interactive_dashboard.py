import pandas as pd

from backend.analytics.interactive_dashboard import DashboardFilters, build_interactive_dashboard


def business_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_date": ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-10"],
            "order_id": [1, 2, 3, 4],
            "customer_segment": ["Enterprise", "SMB", "Enterprise", "SMB"],
            "product": ["A", "B", "A", "C"],
            "category": ["Software", "Services", "Software", "Hardware"],
            "subcategory": ["Analytics", "Support", "Analytics", "Device"],
            "region": ["North", "North", "South", "West"],
            "state": ["NY", "NY", "TX", "CA"],
            "revenue": [100.0, 200.0, 150.0, 50.0],
            "profit": [20.0, 50.0, 30.0, 5.0],
            "quantity": [1, 2, 3, 1],
        }
    )


def register_user(client, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Dashboard User", "password": "StrongPass123"},
    )
    return response.json()["access_token"]


def upload_business_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer Segment,Product,Category,Subcategory,Region,State,Revenue,Profit,Quantity\n"
        b"2026-01-01,1,Enterprise,A,Software,Analytics,North,NY,100,20,1\n"
        b"2026-01-15,2,SMB,B,Services,Support,North,NY,200,50,2\n"
        b"2026-02-01,3,Enterprise,A,Software,Analytics,South,TX,150,30,3\n"
        b"2026-02-10,4,SMB,C,Hardware,Device,West,CA,50,5,1\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("dashboard.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_interactive_dashboard_filters_and_chart_payloads():
    dashboard = build_interactive_dashboard(
        business_dataframe(),
        DashboardFilters(category="Software", region="South", year=2026, month=2),
    )

    assert dashboard["kpis"]["revenue"] == 150.0
    assert dashboard["kpis"]["orders"] == 1
    assert dashboard["filters"]["category"] == ["Hardware", "Services", "Software"]
    assert dashboard["trend"][0]["revenue"] == 150.0
    assert dashboard["product_breakdown"][0]["product"] == "A"
    assert dashboard["correlation_heatmap"]


def test_interactive_dashboard_api_is_user_scoped_and_filterable(client):
    owner_token = register_user(client, "interactive-owner@example.com")
    other_token = register_user(client, "interactive-other@example.com")
    dataset_id = upload_business_dataset(client, owner_token)

    response = client.get(
        f"/datasets/{dataset_id}/dashboard-data",
        params={"category": "Software", "region": "South"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_response = client.get(
        f"/datasets/{dataset_id}/dashboard-data",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kpis"]["revenue"] == 150.0
    assert body["active_filters"] == {"category": "Software", "region": "South"}
    assert body["region_breakdown"][0]["region"] == "South"
    assert forbidden_response.status_code == 404
