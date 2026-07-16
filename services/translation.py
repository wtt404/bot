from deep_translator import GoogleTranslator

from ai.client import chat_completion, looks_like_refusal
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
        choice = response.choices[0]
        result = choice.message.content
        finish_reason = getattr(choice, "finish_reason", None)

        if finish_reason == "content_filter":
            print(f"AI translation blocked by content filter, falling back", flush=True)
        elif result and not looks_like_refusal(text, result):
            return result.strip()
        elif result:
            print(f"AI translation looked like a refusal, falling back: {result[:200]}", flush=True)

    except Exception as e:
        print("AI translation failed:", e, flush=True)

    # Fallback: GoogleTranslator, free and keyless, used whenever the AI
    # path failed or refused.
    try:
        translated = GoogleTranslator(
            source="auto",
            target=settings.TARGET_LANGUAGE.lower()
        ).translate(text)

        return translated

    except Exception as e:
        print("GoogleTranslator failed:", e, flush=True)
        return None
