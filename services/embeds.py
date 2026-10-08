import discord

LANGUAGES = {
    "ar": "Arabic",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ru": "Russian",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "he": "Hebrew",
    "it": "Italian",
    "pt": "Portuguese",
    "fa": "Persian",
}


def _footer(embed, guild):
    if guild:
        embed.set_footer(
            text=guild.name,
            icon_url=guild.icon.url if guild.icon else None
        )


def _author_label(post):
    name = post.author_name
    handle = post.author_handle

    if name and handle and name.lower() != handle.lower():
        return f"{name} (@{handle})"

    if name:
        return name

    if handle:
        return f"@{handle}"

    return None


PLATFORM_LABELS = {
    "x": "X",
    "instagram": "Instagram",
    "telegram": "Telegram",
}


def translation_embed(guild, text, language, media_failed=False):
    embed = discord.Embed(
        description=text or None,
        color=discord.Color.dark_theme()
    )

    _footer(embed, guild)

    if text:
        embed.add_field(
            name="Translated from",
            value=LANGUAGES.get(language, language),
            inline=False
        )

    if media_failed:
        embed.add_field(
            name="⚠️ Media",
            value="Failed to send media due to its size.",
            inline=False
        )

    return embed


def post_embed(guild, post, text, language=None, translated=False, translation_failed=False, media_failed=False):
    if text and len(text) > 4000:
        text = text[:3997] + "..."

    embed = discord.Embed(
        description=text or None,
        color=discord.Color.dark_theme()
    )

    label = _author_label(post)

    if label:
        embed.set_author(
            name=label[:256],
            url=post.url or None,
            icon_url=post.author_avatar or None
        )

    _footer(embed, guild)

    if post.posted_at:
        embed.timestamp = post.posted_at

    if post.url:
        platform = PLATFORM_LABELS.get(post.platform, post.platform.title())
        embed.add_field(
            name="Source",
            value=f"[{platform}]({post.url})",
            inline=False
        )

    if translated:
        embed.add_field(
            name="Translated from",
            value=LANGUAGES.get(language, language) or "Unknown language",
            inline=False
        )

    if translation_failed:
        embed.add_field(
            name="⚠️ Translation",
            value="Couldn't translate this post, showing the original text.",
            inline=False
        )

    if media_failed:
        embed.add_field(
            name="⚠️ Media",
            value="Failed to send media due to its size.",
            inline=False
        )

    return embed
