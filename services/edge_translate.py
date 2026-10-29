import json

import aiohttp

from config import settings

TRANSLATE_URL = "https://edge.microsoft.com/translate/translatetext"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
    ),
    "Content-Type": "application/json",
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


def _target_code():
    name = settings.TARGET_LANGUAGE.strip().lower()
    return TARGET_CODES.get(name, name)


async def translate_text(text):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(
            TRANSLATE_URL,
            params={"from": "", "to": _target_code(), "isEnterpriseClient": "false"},
            data=json.dumps([text]),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:200]
                raise RuntimeError(f"Edge translate returned status {resp.status}: {body}")

            data = await resp.json(content_type=None)

    try:
        return data[0]["translations"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected Edge translate response: {str(data)[:200]}")
