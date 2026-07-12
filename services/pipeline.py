from config import settings
from services.language import detect_language
from services.translation import translate
from services.embeds import translation_embed
from services.media import download, cleanup

async def translate_post(message, post):
    language = detect_language(post.text)

    if language == "en" and settings.IGNORE_ENGLISH:
        translated = None
    else:
        translated = await translate(post.text)
 
    print("Language:", language, flush=True)
    print("Media:", post.media, flush=True)

    media_failed_size = False

    if settings.DOWNLOAD_MEDIA:
        files, media_failed_size = await download(post.media)
    else:
        files = []
    print(f"Files: {len(files)}", flush=True)

    print("Replying...", flush=True)

    embed = None

    if translated or media_failed_size:
        embed = translation_embed(
            message.guild,
            translated,
            language,
            media_failed=media_failed_size
        )

    if embed is None and not files:
        # Nothing worth sending (English post, no translation needed, and
        # no media came through) - don't attempt an empty Discord message.
        print("Nothing to send.", flush=True)
        return

    try:
        await message.reply(
            embed=embed,
            files=files,
            mention_author=False
        )

    finally:
        cleanup(files)

    print("Done", flush=True)