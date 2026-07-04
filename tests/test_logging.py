from pathlib import Path

from tests.test_ai_insights import register_user


def test_operational_logging_writes_upload_event(client, tmp_path):
    token = register_user(client, "logging@example.com")
    content = (
        b"Order Date,Order ID,Customer ID,Product,Region,Revenue,Profit\n"
        b"2026-01-01,1,C1,A,North,100,20\n"
        b"2026-02-01,2,C2,B,South,120,25\n"
    )

    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("log.csv", content, "text/csv")},
    )
    log_path = Path("logs") / "datavista.log"

    assert response.status_code == 201
    assert log_path.exists()
    assert "dataset_uploaded" in log_path.read_text(encoding="utf-8")
