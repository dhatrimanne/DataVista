from __future__ import annotations

import json
from typing import Any, Protocol

import requests
from fastapi import HTTPException, status

from backend.config import get_settings
from backend.utils.logging import get_logger


class InsightClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            get_logger().warning(
                "gemini_request_blocked reason=missing_api_key model=%s",
                self.model,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini is not configured. Set GEMINI_API_KEY in .env to generate AI insights.",
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=90,
            )
        except requests.RequestException as exc:
            get_logger().exception("gemini_request_error model=%s", self.model)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini is temporarily unavailable. Please try again.",
            ) from exc

        if response.status_code >= 400:
            get_logger().error(
                "gemini_request_failed status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini request failed. Verify GEMINI_API_KEY and GEMINI_MODEL.",
            )

        payload = response.json()

        try:
            text = extract_response_text(payload)
            get_logger().info(
                "gemini_request_completed model=%s",
                self.model,
            )
            return text

        except (KeyError, IndexError, TypeError) as exc:
            get_logger().exception(
                "gemini_response_unexpected model=%s",
                self.model,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an unexpected response.",
            ) from exc


def compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def extract_response_text(payload: dict[str, Any]) -> str:
    parts = payload["candidates"][0]["content"]["parts"]
    text = "\n".join(part["text"] for part in parts if isinstance(part.get("text"), str)).strip()
    if not text:
        raise KeyError("No text output found in Gemini response.")
    return text
