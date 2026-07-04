import os
from typing import Any

import requests


API_BASE_URL = os.getenv("DATAVISTA_API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT_SECONDS = 20
AI_TIMEOUT_SECONDS = 120


class ApiError(Exception):
    pass


def request_json(
    method: str,
    path: str,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    **kwargs: Any,
) -> dict[str, Any]:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=timeout, **kwargs)
    except requests.Timeout as exc:
        raise ApiError("The request is still processing. Please try again in a moment.") from exc
    except requests.RequestException as exc:
        raise ApiError("DataVista could not reach the backend service. Please verify it is running.") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Request failed.")
        except ValueError:
            detail = "Request failed."
        raise ApiError(str(detail))
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


def register(email: str, full_name: str, password: str) -> dict[str, Any]:
    return request_json(
        "POST",
        "/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )


def login(email: str, password: str, remember_me: bool) -> dict[str, Any]:
    return request_json(
        "POST",
        "/auth/login",
        json={"email": email, "password": password, "remember_me": remember_me},
    )


def fetch_profile(token: str) -> dict[str, Any]:
    return request_json("GET", "/auth/me", token=token)


def update_profile(token: str, full_name: str) -> dict[str, Any]:
    return request_json("PATCH", "/auth/me", token=token, json={"full_name": full_name})


def change_password(token: str, current_password: str, new_password: str) -> None:
    request_json(
        "PATCH",
        "/auth/password",
        token=token,
        json={"current_password": current_password, "new_password": new_password},
    )


def update_preferences(token: str, theme: str, preferred_gemini_model: str | None) -> dict[str, Any]:
    return request_json(
        "PATCH",
        "/auth/preferences",
        token=token,
        json={"theme": theme, "preferred_gemini_model": preferred_gemini_model},
    )


def delete_account(token: str) -> None:
    request_json("DELETE", "/auth/me", token=token)


def fetch_dashboard_summary(token: str) -> dict[str, Any]:
    return request_json("GET", "/dashboard/summary", token=token)


def logout(token: str) -> None:
    request_json("POST", "/auth/logout", token=token)


def upload_dataset(token: str, filename: str, content: bytes, remove_outliers: bool = False) -> dict[str, Any]:
    files = {"file": (filename, content)}
    return request_json("POST", "/datasets", token=token, params={"remove_outliers": remove_outliers}, files=files)


def list_datasets(token: str) -> list[dict[str, Any]]:
    return request_json("GET", "/datasets", token=token)["datasets"]


def get_dataset_detail(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("GET", f"/datasets/{dataset_id}", token=token)


def rename_dataset(token: str, dataset_id: int, name: str) -> dict[str, Any]:
    return request_json("PATCH", f"/datasets/{dataset_id}", token=token, json={"name": name})


def reanalyze_dataset(token: str, dataset_id: int, remove_outliers: bool = False) -> dict[str, Any]:
    return request_json(
        "POST",
        f"/datasets/{dataset_id}/reanalyze",
        token=token,
        params={"remove_outliers": remove_outliers},
    )


def delete_dataset(token: str, dataset_id: int) -> None:
    request_json("DELETE", f"/datasets/{dataset_id}", token=token)


def download_cleaned_dataset(token: str, dataset_id: int) -> bytes:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}/download-cleaned", headers=headers, timeout=20)
    if response.status_code >= 400:
        raise ApiError("Could not download cleaned dataset.")
    return response.content


def get_dataset_analysis(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("GET", f"/datasets/{dataset_id}/analysis", token=token)


def regenerate_dataset_analysis(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("POST", f"/datasets/{dataset_id}/analysis", token=token)


def get_interactive_dashboard(token: str, dataset_id: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    params = {key: value for key, value in (filters or {}).items() if value not in (None, "", [])}
    return request_json("GET", f"/datasets/{dataset_id}/dashboard-data", token=token, params=params)


def generate_machine_learning(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("POST", f"/datasets/{dataset_id}/ml", token=token)


def generate_business_insights(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("POST", f"/datasets/{dataset_id}/insights", token=token, timeout=AI_TIMEOUT_SECONDS)


def ask_dataset_question(token: str, dataset_id: int, question: str) -> dict[str, Any]:
    return request_json(
        "POST",
        f"/datasets/{dataset_id}/chat",
        token=token,
        json={"question": question},
        timeout=AI_TIMEOUT_SECONDS,
    )


def get_recommendations(token: str, dataset_id: int) -> dict[str, Any]:
    return request_json("GET", f"/datasets/{dataset_id}/recommendations", token=token)


def list_reports(token: str) -> list[dict[str, Any]]:
    return request_json("GET", "/reports", token=token)["reports"]


def create_report(token: str, dataset_id: int, include_ai_insights: bool = False) -> dict[str, Any]:
    return request_json(
        "POST",
        "/reports",
        token=token,
        json={"dataset_id": dataset_id, "include_ai_insights": include_ai_insights},
        timeout=AI_TIMEOUT_SECONDS if include_ai_insights else DEFAULT_TIMEOUT_SECONDS,
    )["report"]


def download_report(token: str, report_id: int) -> bytes:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/reports/{report_id}/download", headers=headers, timeout=30)
    if response.status_code >= 400:
        raise ApiError("Could not download report.")
    return response.content


def delete_report(token: str, report_id: int) -> None:
    request_json("DELETE", f"/reports/{report_id}", token=token)


def list_notifications(token: str, limit: int = 20) -> list[dict[str, Any]]:
    return request_json("GET", "/notifications", token=token, params={"limit": limit})
