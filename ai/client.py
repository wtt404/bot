
from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# Tried in order. "openrouter/free" is OpenRouter's own auto-router - it picks
# from whatever free models are currently available, which matters because
# the free model lineup on OpenRouter rotates often (models get pulled or
# rate-limited without notice). The pinned model after it is a long-standing,
# stable free model kept as a backup in case the auto-router itself has an
# issue, giving us redundancy across providers rather than a single point of
# failure.
FALLBACK_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


async def chat_completion(messages, tools=None, **kwargs):
    """Try each fallback model in order, returning the first success."""
    last_error = None

    for model in FALLBACK_MODELS:
        try:
            kwargs_with_tools = dict(kwargs)
            if tools:
                kwargs_with_tools["tools"] = tools

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs_with_tools,
            )
            return response

        except Exception as e:
            print(f"Model '{model}' failed: {e}", flush=True)
            last_error = e
            continue

    raise last_error