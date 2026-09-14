import asyncio
import time

from deep_translator import GoogleTranslator, MyMemoryTranslator

from config import settings


def _looks_like_bad_response(text: str) -> bool:
    if not text:
        return True

    lowered = text.lower()

    # Both providers have been observed occasionally handing back a raw
    # server-error page as if it were a real translation, rather than
    # raising a clean exception. Catch the common shapes of that here.
    error_markers = (
        "that's an error", "that's all we know", "<html",
        "error 500", "error 404", "error 429",
        "too many requests",
    )

    return any(marker in lowered for marker in error_markers)


class _Throttle:

    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._last_call_at = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            now = time.monotonic()
            remaining = self._min_interval - (now - self._last_call_at)

            if remaining > 0:
                await asyncio.sleep(remaining)

            self._last_call_at = time.monotonic()

_google_throttle = _Throttle(0.4)

_mymemory_throttle = _Throttle(1.0)


async def _run_sync(throttle: "_Throttle", func, *args) -> str:
    await throttle.wait()

    return await asyncio.to_thread(func, *args)


async def _try_provider(name: str, throttle: "_Throttle", translate_fn, text: str, attempts: int) -> str:
    for attempt in range(attempts):
        try:
            result = await _run_sync(throttle, translate_fn, text)

            if _looks_like_bad_response(result):
                print(
                    f"{name} returned a suspicious response "
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
            print(f"{name} failed (attempt {attempt + 1}/{attempts}):", e, flush=True)
            if attempt < attempts - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return None

    return None

_MYMEMORY_SOURCE_NAMES = {
    "en": "english",
    "ar": "arabic",
    "ja": "japanese",
    "ko": "korean",
    "zh": "chinese simplified",
    "ru": "russian",
    "fr": "french",
    "de": "german",
    "uk": "ukrainian",
    "es": "spanish",
    "he": "hebrew",
    "it": "italian",
    "pt": "portuguese",
    "fa": "persian",
}


async def translate(text: str, source_language: str = None) -> str:
    target = settings.TARGET_LANGUAGE.lower()

    result = await _try_provider(
        "GoogleTranslator",
        _google_throttle,
        GoogleTranslator(source="auto", target=target).translate,
        text,
        attempts=3,
    )

    if result:
        return result

    print("GoogleTranslator exhausted, falling back to MyMemoryTranslator", flush=True)

    mymemory_source = _MYMEMORY_SOURCE_NAMES.get(source_language) if source_language else None

    if not mymemory_source:
        print(f"No usable MyMemory source name for '{source_language}' - skipping fallback", flush=True)
        return None

    result = await _try_provider(
        "MyMemoryTranslator",
        _mymemory_throttle,
        MyMemoryTranslator(source=mymemory_source, target=target).translate,
        text,
        attempts=2,
    )

    return result
