from deep_translator import GoogleTranslator

from ai.client import chat_completion
from config import settings

SYSTEM_PROMPT = f"""
You are a professional translator.

Translate the user's text into {settings.TARGET_LANGUAGE}.

Rules:
- Preserve the original meaning.
- Preserve formatting.
- Do not add explanations.
- Do not summarize.
- Output only the translation.
"""


async def translate(text: str) -> str:
    # Primary: AI translation via OpenRouter's fallback chain.
    try:
        response = await chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        result = response.choices[0].message.content

        if result:
            return result.strip()

    except Exception as e:
        print("AI translation failed:", e, flush=True)

    # Fallback: GoogleTranslator, free and keyless, used only if every AI
    # model in the fallback chain failed.
    try:
        translated = GoogleTranslator(
            source="auto",
            target=settings.TARGET_LANGUAGE.lower()
        ).translate(text)

        return translated

    except Exception as e:
        print("GoogleTranslator failed:", e, flush=True)
        return None