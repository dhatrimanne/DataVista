from tests.test_ai_insights import register_user


def test_user_settings_profile_preferences_password_and_delete(client):
    token = register_user(client, "settings@example.com")

    profile_response = client.patch(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Settings User"},
    )
    preferences_response = client.patch(
        "/auth/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"theme": "dark", "preferred_gemini_model": "gemini-1.5-flash"},
    )
    bad_password_response = client.patch(
        "/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong", "new_password": "NewStrongPass123"},
    )
    password_response = client.patch(
        "/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "StrongPass123", "new_password": "NewStrongPass123"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "settings@example.com", "password": "NewStrongPass123", "remember_me": False},
    )
    new_token = login_response.json()["access_token"]
    delete_response = client.delete("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    disabled_login_response = client.post(
        "/auth/login",
        json={"email": "settings@example.com", "password": "NewStrongPass123", "remember_me": False},
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "Settings User"
    assert preferences_response.status_code == 200
    assert preferences_response.json()["theme"] == "dark"
    assert bad_password_response.status_code == 400
    assert password_response.status_code == 200
    assert login_response.status_code == 200
    assert delete_response.status_code == 200
    assert disabled_login_response.status_code == 403
