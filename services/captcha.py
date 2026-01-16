from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import get_settings


async def verify_captcha(token: Optional[str], remote_ip: str | None = None) -> bool:
    settings = get_settings()
    if not settings.captcha_provider or not settings.captcha_secret_key:
        return True  # captcha not configured

    if not token:
        return False

    provider = settings.captcha_provider.lower()

    if provider == "hcaptcha":
        url = "https://hcaptcha.com/siteverify"
        payload = {"secret": settings.captcha_secret_key, "response": token}
        if remote_ip:
            payload["remoteip"] = remote_ip
    elif provider == "recaptcha":
        url = "https://www.google.com/recaptcha/api/siteverify"
        payload = {"secret": settings.captcha_secret_key, "response": token}
        if remote_ip:
            payload["remoteip"] = remote_ip
    elif provider == "turnstile":
        url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        payload = {"secret": settings.captcha_secret_key, "response": token}
        if remote_ip:
            payload["remoteip"] = remote_ip
    else:
        return True

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, data=payload)
        r.raise_for_status()
        data = r.json()

    return bool(data.get("success"))
