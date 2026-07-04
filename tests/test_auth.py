def register_user(client, email="owner@example.com", password="StrongPass123"):
    return client.post(
        "/auth/register",
        json={"email": email, "full_name": "Data Owner", "password": password},
    )


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_returns_token_and_profile(client):
    response = register_user(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "owner@example.com"
    assert "hashed_password" not in body["user"]


def test_register_rejects_duplicate_email(client):
    assert register_user(client).status_code == 201

    response = register_user(client)

    assert response.status_code == 409


def test_login_and_profile_access(client):
    assert register_user(client).status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass123", "remember_me": True},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    profile_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_response.status_code == 200
    assert profile_response.json()["last_login_at"] is not None


def test_login_rejects_bad_password(client):
    assert register_user(client).status_code == 201

    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_logout_revokes_token(client):
    register_response = register_user(client)
    token = register_response.json()["access_token"]

    logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    profile_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert logout_response.status_code == 200
    assert profile_response.status_code == 401
