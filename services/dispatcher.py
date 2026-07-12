from services.fetchers import FETCHERS
from services.pipeline import translate_post

async def dispatch(message, result):
    fetcher = FETCHERS.get(result.type)

    if fetcher is None:
        return

    try:
        post = await fetcher.fetch(result.url)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Fetch failed for {result.type} ({result.url}): {e}", flush=True)
        await message.reply(
            f"Couldn't fetch that {result.type} post: {e}",
            mention_author=False
        )
        return

    try:
        await translate_post(message, post)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"translate_post failed: {e}", flush=True)
        await message.reply(
            "Something went wrong while processing that post.",
            mention_author=False
        )