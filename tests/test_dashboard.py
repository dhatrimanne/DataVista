def register_user(client, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Dashboard User", "password": "StrongPass123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard/summary")

    assert response.status_code == 401


def test_dashboard_empty_workspace_summary(client):
    token = register_user(client, "dashboard@example.com")

    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total_datasets"] == 0
    assert body["total_reports"] == 0
    assert body["ai_insights_generated"] == 0
    assert body["forecasts_generated"] == 0
    assert body["business_health_score"] is None
    assert "upload and analyze" in body["business_health_status"]
    assert body["recent_activity"][0]["event_type"] == "account_created"


def test_dashboard_records_login_activity(client):
    register_user(client, "activity@example.com")

    login_response = client.post(
        "/auth/login",
        json={"email": "activity@example.com", "password": "StrongPass123", "remember_me": False},
    )
    token = login_response.json()["access_token"]
    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    event_types = [event["event_type"] for event in response.json()["recent_activity"]]
    assert event_types[:2] == ["login", "account_created"]


def test_dashboard_is_scoped_to_current_user(client):
    first_token = register_user(client, "first@example.com")
    second_token = register_user(client, "second@example.com")

    from backend.auth.security import decode_access_token
    from backend.database.connection import db_session

    first_user_id = int(decode_access_token(first_token))
    with db_session() as connection:
        connection.execute(
            "INSERT INTO datasets (user_id, name, status) VALUES (?, ?, ?)",
            (first_user_id, "Private revenue.csv", "analyzed"),
        )

    first_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {first_token}"})
    second_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {second_token}"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["total_datasets"] == 1
    assert second_response.json()["total_datasets"] == 0
    assert first_response.json()["recent_activity"][0]["message"] == "Account created."
    assert second_response.json()["recent_activity"][0]["message"] == "Account created."


def test_dashboard_business_health_uses_latest_dataset_analysis(client):
    token = register_user(client, "health-dashboard@example.com")
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,100,20\n"
        b"2026-01-15,2,C1,B,North,200,50\n"
        b"2026-02-01,3,C2,A,South,180,45\n"
        b"2026-02-10,4,C3,C,West,120,20\n"
    )
    upload_response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("health.csv", content, "text/csv")},
    )
    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert upload_response.status_code == 201
    body = response.json()
    assert body["business_health_score"] is not None
    assert body["business_health_factors"]
    assert "performance" in body["business_health_status"].lower()
