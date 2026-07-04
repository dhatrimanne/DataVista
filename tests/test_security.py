from tests.test_ai_insights import register_user


def test_security_headers_are_applied(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_upload_rejects_mismatched_content_type(client):
    token = register_user(client, "security@example.com")

    response = client.post(
        "/datasets",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bad.csv", b"not,really\n1,2\n", "application/pdf")},
    )

    assert response.status_code == 400
    assert "content type" in response.json()["detail"]
