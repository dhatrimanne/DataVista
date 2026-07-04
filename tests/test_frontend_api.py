from __future__ import annotations

import requests
import pytest

from frontend.utils import api


class DummyResponse:
    status_code = 200
    content = b"{}"

    def json(self) -> dict:
        return {}


def test_ai_insights_uses_extended_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, int] = {}

    def fake_request(method: str, url: str, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return DummyResponse()

    monkeypatch.setattr(api.requests, "request", fake_request)

    api.generate_business_insights("token", 1)

    assert captured["timeout"] == api.AI_TIMEOUT_SECONDS


def test_ai_chat_uses_extended_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, int] = {}

    def fake_request(method: str, url: str, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return DummyResponse()

    monkeypatch.setattr(api.requests, "request", fake_request)

    api.ask_dataset_question("token", 1, "What changed?")

    assert captured["timeout"] == api.AI_TIMEOUT_SECONDS


def test_ai_report_uses_extended_timeout_only_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[int] = []

    class ReportResponse(DummyResponse):
        def json(self) -> dict:
            return {"report": {"id": 1}}

    def fake_request(method: str, url: str, **kwargs):
        captured.append(kwargs["timeout"])
        return ReportResponse()

    monkeypatch.setattr(api.requests, "request", fake_request)

    api.create_report("token", 1, include_ai_insights=False)
    api.create_report("token", 1, include_ai_insights=True)

    assert captured == [api.DEFAULT_TIMEOUT_SECONDS, api.AI_TIMEOUT_SECONDS]


def test_request_timeout_returns_user_friendly_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(method: str, url: str, **kwargs):
        raise requests.ReadTimeout("timed out")

    monkeypatch.setattr(api.requests, "request", fake_request)

    with pytest.raises(api.ApiError, match="still processing"):
        api.generate_business_insights("token", 1)
