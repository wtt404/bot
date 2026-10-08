from config import settings
from services.language import detect_language
from services.translation import translate
from services.embeds import post_embed
from services.media import download, cleanup


async def _suppress_original_embed(message):
    edit = getattr(message, "edit", None)

    if edit is None:
        return

    try:
        await edit(suppress=True)
    except Exception as e:
        print(f"Couldn't suppress original embed: {e}", flush=True)


async def translate_post(message, post):
    text = (post.text or "").strip()
    language = None
    shown_text = text
    translated = False
    translation_failed = False

    if text:
        language = detect_language(text)

        if not (language == "en" and settings.IGNORE_ENGLISH):
            result = await translate(text, source_language=language)

            if result:
                shown_text = result
                translated = True
            else:
                translation_failed = True

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

    if shown_text or post.author_name or post.author_handle or media_failed_size:
        embed = post_embed(
            message.guild,
            post,
            shown_text,
            language=language,
            translated=translated,
            translation_failed=translation_failed,
            media_failed=media_failed_size
        )

    if embed is None and not files:
        print("Nothing to send.", flush=True)
        return

    try:
        await message.reply(
            embed=embed,
            files=files,
            mention_author=False
        )

        await _suppress_original_embed(message)

    finally:
        cleanup(files)

    print("Done", flush=True)
