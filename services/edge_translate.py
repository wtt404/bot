import asyncio
import base64
import json
import time

import aiohttp

from config import settings

AUTH_URL = "https://edge.microsoft.com/translate/auth"
TRANSLATE_URL = "https://api-edge.cognitive.microsofttranslator.com/translate"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    ),
}

TARGET_CODES = {
    "english": "en",
    "arabic": "ar",
    "indonesian": "id",
    "turkish": "tr",
    "persian": "fa",
    "hebrew": "he",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh-Hans",
    "russian": "ru",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "ukrainian": "uk",
}

_token = None
_expires_at = 0.0
_lock = asyncio.Lock()


def _target_code():
    name = settings.TARGET_LANGUAGE.strip().lower()
    return TARGET_CODES.get(name, name)


def _token_expiry(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:
        return time.time() + 300


async def _get_token(session, force=False):
    global _token, _expires_at

    async with _lock:
        if not force and _token and time.time() < _expires_at - 60:
            return _token

        async with session.get(AUTH_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Edge auth returned status {resp.status}")

            token = (await resp.text()).strip()

        if not token:
            raise RuntimeError("Edge auth returned an empty token")

        _token = token
        _expires_at = _token_expiry(token)

        return _token


async def _request(session, token, text):
    async with session.post(
        TRANSLATE_URL,
        params={"to": _target_code(), "api-version": "3.0", "includeSentenceLength": "true"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps([{"Text": text}]),
        timeout=aiohttp.ClientTimeout(total=20),
    ) as resp:
        if resp.status == 401:
            return None, 401

        if resp.status != 200:
            body = (await resp.text())[:200]
            raise RuntimeError(f"Edge translate returned status {resp.status}: {body}")

        return await resp.json(content_type=None), 200


async def translate_text(text):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        token = await _get_token(session)
        data, status = await _request(session, token, text)

        if status == 401:
            token = await _get_token(session, force=True)
            data, status = await _request(session, token, text)

            if status == 401:
                raise RuntimeError("Edge translate rejected a fresh token")

    try:
        return data[0]["translations"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected Edge translate response: {str(data)[:200]}")
