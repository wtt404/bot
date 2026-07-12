import discord

def translation_embed(guild, text, language, media_failed=False):
    embed = discord.Embed(
        description=text or None,
        color=discord.Color.dark_theme()
    )

    embed.set_footer(
        text=guild.name,
        icon_url=guild.icon.url if guild.icon else None
    )

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
    }

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