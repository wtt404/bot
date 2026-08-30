import asyncio

from deep_translator import GoogleTranslator

from config import settings


def _looks_like_bad_response(text: str) -> bool:
    if not text:
        return True

    lowered = text.lower()

    error_markers = (
        "that's an error", "that's all we know", "<html",
        "error 500", "error 404", "error 429",
    )

    return any(marker in lowered for marker in error_markers)


async def _translate_once(text: str) -> str:
    
    return await asyncio.to_thread(
        GoogleTranslator(
            source="auto",
            target=settings.TARGET_LANGUAGE.lower()
        ).translate,
        text
    )


async def translate(text: str) -> str:
    for attempt in range(2):
        try:
            result = await _translate_once(text)

            if _looks_like_bad_response(result):
                print(
                    f"GoogleTranslator returned a suspicious response "
                    f"(attempt {attempt + 1}/2), discarding: "
                    f"{(result or '')[:200]}",
                    flush=True
                )
                if attempt == 0:
                    await asyncio.sleep(1.5)
                    continue
                return None

            return result

        except Exception as e:
            print(f"GoogleTranslator failed (attempt {attempt + 1}/2):", e, flush=True)
            if attempt == 0:
                await asyncio.sleep(1.5)
                continue
            return None

    return None
