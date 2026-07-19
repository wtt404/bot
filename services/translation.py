from deep_translator import GoogleTranslator

from config import settings


async def translate(text: str) -> str:
    try:
        return GoogleTranslator(
            source="auto",
            target=settings.TARGET_LANGUAGE.lower()
        ).translate(text)

    except Exception as e:
        print("GoogleTranslator failed:", e, flush=True)
        return None
