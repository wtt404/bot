import asyncio
import time

from deep_translator import GoogleTranslator

from config import settings


_MIN_INTERVAL = 0.4  
_last_call_at = 0.0
_throttle_lock = asyncio.Lock()


def _looks_like_bad_response(text: str) -> bool:
    if not text:
        return True

    lowered = text.lower()

    error_markers = (
        "that's an error", "that's all we know", "<html",
        "error 500", "error 404", "error 429",
        "too many requests",
    )

    return any(marker in lowered for marker in error_markers)


async def _throttle():
    global _last_call_at

    async with _throttle_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call_at)

        if wait > 0:
            await asyncio.sleep(wait)

        _last_call_at = time.monotonic()


async def _translate_once(text: str) -> str:
    await _throttle()

    return await asyncio.to_thread(
        GoogleTranslator(
            source="auto",
            target=settings.TARGET_LANGUAGE.lower()
        ).translate,
        text
    )


async def translate(text: str) -> str:
    attempts = 3

    for attempt in range(attempts):
        try:
            result = await _translate_once(text)

            if _looks_like_bad_response(result):
                print(
                    f"GoogleTranslator returned a suspicious response "
                    f"(attempt {attempt + 1}/{attempts}), discarding: "
                    f"{(result or '')[:200]}",
                    flush=True
                )
                if attempt < attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s
                    continue
                return None

            return result

        except Exception as e:
            print(f"GoogleTranslator failed (attempt {attempt + 1}/{attempts}):", e, flush=True)
            if attempt < attempts - 1:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s
                continue
            return None

    return None
