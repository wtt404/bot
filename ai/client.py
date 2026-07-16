import time

from openai import AsyncOpenAI

from config import OPENROUTER_API_KEY

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    timeout=15.0,  # fail fast into the next fallback model instead of the
                   # SDK's 10-minute default - a hung request shouldn't make
                   # every feature in the bot feel slow.
    max_retries=0,  # we already retry across models ourselves below; the
                     # SDK's own default (2 retries) was silently retrying
                     # the SAME already-rate-limited model 2-3 times before
                     # our fallback loop ever got a turn, turning a ~2s
                     # rejection into a 40+ second wait.
)

# Tried in order. "openrouter/free" (OpenRouter's own auto-router) goes
# first - real timing data showed it succeeding in ~11s while a specific
# pinned model was actively rate-limited upstream and took 44s+ to fail.
# Free models on OpenRouter get rate-limited/pulled unpredictably, so
# rather than gamble on a static order, the auto-router (which picks
# whatever's currently healthy) goes first, with a pinned model as backup
# in case the auto-router itself has an issue.
FALLBACK_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


async def chat_completion(messages, tools=None, **kwargs):
    """Try each fallback model in order, returning the first success."""
    last_error = None
    overall_start = time.monotonic()

    for model in FALLBACK_MODELS:
        try:
            kwargs_with_tools = dict(kwargs)
            if tools:
                kwargs_with_tools["tools"] = tools

            attempt_start = time.monotonic()

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs_with_tools,
            )

            elapsed = time.monotonic() - attempt_start
            total = time.monotonic() - overall_start
            print(f"[TIMING] chat_completion: model='{model}' succeeded in {elapsed:.2f}s (total {total:.2f}s)", flush=True)

            return response

        except Exception as e:
            elapsed = time.monotonic() - attempt_start
            print(f"[TIMING] chat_completion: model='{model}' failed after {elapsed:.2f}s: {e}", flush=True)
            last_error = e
            continue

    raise last_error


# Free models occasionally refuse sensitive news content (war, death,
# politics - exactly what this bot handles a lot of) with a plain-text
# refusal instead of raising an error or a proper content_filter finish
# reason, so callers need to check the actual text too, not just for
# exceptions. This is a heuristic, not bulletproof, but catches the common
# refusal phrasing. Shared by translate/summarize/any future text tool.
REFUSAL_MARKERS = (
    "i cannot", "i can't", "i'm sorry", "i am sorry", "i'm not able",
    "i am not able", "as an ai", "as a language model", "content policy",
    "cannot assist", "can't assist", "cannot help with", "unable to translate",
    "safety guidelines", "user safety", "i won't", "i will not",
    "against my", "not appropriate", "i must decline", "i'm unable",
)


def looks_like_refusal(original: str, result: str) -> bool:
    lowered = result.strip().lower()

    if any(marker in lowered for marker in REFUSAL_MARKERS):
        return True

    # A real translation/summary is roughly proportional in length to the
    # source; a refusal is typically a short, unrelated sentence.
    if len(original) > 80 and len(result) < len(original) * 0.25:
        return True

    return False
