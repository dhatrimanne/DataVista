from tests.test_ai_insights import register_user


def test_notifications_are_user_scoped_and_include_workflow_events(client):
    owner_token = register_user(client, "notify-owner@example.com")
    other_token = register_user(client, "notify-other@example.com")
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,100,20\n"
        b"2026-02-01,2,C2,B,South,120,25\n"
        b"2026-03-01,3,C3,A,North,140,30\n"
    )

    upload_response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("notify.csv", content, "text/csv")},
    )
    owner_response = client.get("/notifications", headers={"Authorization": f"Bearer {owner_token}"})
    other_response = client.get("/notifications", headers={"Authorization": f"Bearer {other_token}"})

    assert upload_response.status_code == 201
    owner_types = [item["event_type"] for item in owner_response.json()]
    other_types = [item["event_type"] for item in other_response.json()]
    assert "dataset_uploaded" in owner_types
    assert "cleaning_completed" in owner_types
    assert "analysis_completed" in owner_types
    assert "dataset_uploaded" not in other_types
