def register_user(client, email: str = "datasets@example.com") -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "full_name": "Dataset Owner", "password": "StrongPass123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def upload_csv(client, token: str, filename: str = "sales.csv"):
    content = b"Order ID,Revenue,Region\n1,100,North\n2,,South\n2,,South\n"
    return client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "text/csv")},
    )


def test_dataset_upload_lists_metadata_and_updates_dashboard(client):
    token = register_user(client)

    upload_response = upload_csv(client, token)
    list_response = client.get("/datasets", headers={"Authorization": f"Bearer {token}"})
    dashboard_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["name"] == "sales"
    assert uploaded["row_count"] == 2
    assert uploaded["column_count"] == 3
    assert uploaded["missing_value_count"] == 0
    assert uploaded["data_quality_score"] is not None
    assert uploaded["status"] == "analyzed"
    assert list_response.json()["datasets"][0]["id"] == uploaded["id"]
    assert dashboard_response.json()["total_datasets"] == 1


def test_dataset_detail_rename_reanalyze_and_download(client):
    token = register_user(client)
    dataset = upload_csv(client, token).json()

    rename_response = client.patch(
        f"/datasets/{dataset['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Quarterly Sales"},
    )
    reanalyze_response = client.post(
        f"/datasets/{dataset['id']}/reanalyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    detail_response = client.get(f"/datasets/{dataset['id']}", headers={"Authorization": f"Bearer {token}"})
    download_response = client.get(
        f"/datasets/{dataset['id']}/download-cleaned",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "Quarterly Sales"
    assert reanalyze_response.status_code == 200
    assert reanalyze_response.json()["row_count"] == 2
    assert detail_response.status_code == 200
    assert detail_response.json()["cleaning_report"]["duplicates_removed"] == 1
    assert [event["event_type"] for event in detail_response.json()["history"]][:3] == [
        "reanalyzed",
        "renamed",
        "uploaded",
    ]
    assert download_response.status_code == 200
    assert b"order_id,revenue,region" in download_response.content.lower()


def test_dataset_delete_removes_record(client):
    token = register_user(client)
    dataset = upload_csv(client, token).json()

    delete_response = client.delete(f"/datasets/{dataset['id']}", headers={"Authorization": f"Bearer {token}"})
    detail_response = client.get(f"/datasets/{dataset['id']}", headers={"Authorization": f"Bearer {token}"})

    assert delete_response.status_code == 204
    assert detail_response.status_code == 404


def test_dataset_upload_rejects_unsupported_file_type(client):
    token = register_user(client)

    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"not,a,dataset", "text/plain")},
    )

    assert response.status_code == 400


def test_dataset_upload_accepts_latin1_csv(client):
    token = register_user(client, "latin1@example.com")
    content = b"Order Date,Customer,Revenue\n2026-01-01,Caf\xe9,100\n2026-01-02,Ni\xf1o,120\n"

    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("latin1.csv", content, "text/csv")},
    )

    assert response.status_code == 201
    assert response.json()["row_count"] == 2


def test_dataset_upload_prevents_duplicate_content(client):
    token = register_user(client, "duplicate@example.com")
    content = b"Order Date,Customer,Revenue\n2026-01-01,A,100\n2026-01-02,B,120\n"

    first_response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("first.csv", content, "text/csv")},
    )
    duplicate_response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("second.csv", content, "text/csv")},
    )
    list_response = client.get("/datasets", headers={"Authorization": f"Bearer {token}"})

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert len(list_response.json()["datasets"]) == 1


def test_dataset_access_is_user_scoped(client):
    owner_token = register_user(client, "owner@example.com")
    other_token = register_user(client, "other@example.com")
    dataset = upload_csv(client, owner_token).json()

    detail_response = client.get(f"/datasets/{dataset['id']}", headers={"Authorization": f"Bearer {other_token}"})
    download_response = client.get(
        f"/datasets/{dataset['id']}/download-cleaned",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert detail_response.status_code == 404
    assert download_response.status_code == 404
