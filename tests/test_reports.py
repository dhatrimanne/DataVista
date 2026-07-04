from tests.test_ai_insights import register_user
from backend.reports.generator import ai_markdown_flowables, styles


def upload_report_dataset(client, token: str) -> int:
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,100,20\n"
        b"2026-02-01,2,C2,B,South,120,25\n"
        b"2026-03-01,3,C3,A,North,140,30\n"
    )
    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("report.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_report_center_generates_downloads_deletes_and_scopes_reports(client):
    owner_token = register_user(client, "report-owner@example.com")
    other_token = register_user(client, "report-other@example.com")
    dataset_id = upload_report_dataset(client, owner_token)

    create_response = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"dataset_id": dataset_id, "include_ai_insights": False},
    )
    report = create_response.json()["report"]
    list_response = client.get("/reports", headers={"Authorization": f"Bearer {owner_token}"})
    other_list_response = client.get("/reports", headers={"Authorization": f"Bearer {other_token}"})
    download_response = client.get(
        f"/reports/{report['id']}/download",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    forbidden_download = client.get(
        f"/reports/{report['id']}/download",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    dashboard_response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {owner_token}"})
    delete_response = client.delete(
        f"/reports/{report['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    missing_download = client.get(
        f"/reports/{report['id']}/download",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert create_response.status_code == 201
    assert list_response.json()["reports"][0]["id"] == report["id"]
    assert other_list_response.json()["reports"] == []
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"%PDF")
    assert forbidden_download.status_code == 404
    assert dashboard_response.json()["total_reports"] == 1
    assert delete_response.status_code == 204
    assert missing_download.status_code == 404


def test_report_generation_continues_when_gemini_is_unavailable(client):
    token = register_user(client, "report-no-gemini@example.com")
    dataset_id = upload_report_dataset(client, token)

    response = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={"dataset_id": dataset_id, "include_ai_insights": True},
    )

    assert response.status_code == 201
    assert response.json()["report"]["file_size_bytes"] > 0


def test_ai_markdown_flowables_preserve_readable_markdown_structure():
    flowables = ai_markdown_flowables(
        "## Executive Summary\n\nThe dataset shows **strong revenue**.\n\n- Promote Canon imageCLASS 2200 Advanced Copier\n- Watch margin risk",
        styles(),
    )

    paragraphs = [item for item in flowables if item.__class__.__name__ == "Paragraph"]

    assert len(paragraphs) == 4
    assert paragraphs[0].style.name == "AIHeading"
    assert paragraphs[1].style.name == "AIBody"
    assert paragraphs[2].style.name == "AIBullet"
    assert paragraphs[1].style.leading > paragraphs[1].style.fontSize
