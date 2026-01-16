from __future__ import annotations

import json
from typing import Any, Optional

import httpx


class GeminiClient:
    """Minimal Gemini API client (HTTP).

    This is intentionally lightweight and meant as a starting point.

    Required environment variables:
      - GEMINI_API_KEY

    Optional environment variables:
      - GEMINI_MODEL (default: "gemini-1.5-pro")
      - GEMINI_BASE_URL (default: "https://generativelanguage.googleapis.com")

    The endpoint style used here follows the Generative Language API (v1beta).
    If your Gemini endpoint/provider differs, adjust `generate_content` accordingly.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", base_url: str = "https://generativelanguage.googleapis.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate_content(self, prompt: str, *, temperature: float = 0.2, response_mime_type: Optional[str] = None) -> dict[str, Any]:
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        params = {"key": self.api_key}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, params=params, json=payload)
            r.raise_for_status()
            return r.json()

    async def generate_json(self, prompt: str) -> dict[str, Any]:
        """Convenience: ask Gemini to respond with JSON and parse it."""
        raw = await self.generate_content(
            prompt + "\n\nReturn ONLY valid JSON.",
            temperature=0.0,
            response_mime_type="application/json",
        )
        # The response format may vary. We attempt to extract the first candidate text.
        try:
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception:
            return {"raw": raw}
