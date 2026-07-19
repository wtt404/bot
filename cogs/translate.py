import discord
from discord.ext import commands
from discord import app_commands


class InteractionReplyAdapter:
    """Lets services.dispatcher/pipeline (built around discord.Message.reply)
    be reused unchanged from a slash command's Interaction."""

    def __init__(self, interaction: discord.Interaction):
        self._interaction = interaction
        self.guild = interaction.guild

    async def reply(self, *, content=None, embed=None, files=None, **kwargs):
        await self._interaction.followup.send(
            content=content if content is not None else discord.utils.MISSING,
            embed=embed if embed is not None else discord.utils.MISSING,
            files=files if files else discord.utils.MISSING,
        )


class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("TRANSLATE COG INITIALIZED", flush=True)

    @app_commands.command(name="translate", description="Translate text, or fetch + translate an X/Telegram link")
    @app_commands.describe(text="Text to translate, or a link to an X/Telegram post")
    async def translate(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer()
        print(f"COMMAND /translate | user={interaction.user.id}", flush=True)

        from services.detector import detect
        from services.dispatcher import dispatch

        detected = detect(text)

        if detected:
            # An X/Telegram link was pasted: reuse the normal fetch + media pipeline.
            adapter = InteractionReplyAdapter(interaction)
            await dispatch(adapter, detected)
            return

        # Plain text: translate it directly.
        from services.language import detect_language
        from services.translation import translate as translate_text
        from services.embeds import translation_embed

        language = detect_language(text)
        translated = await translate_text(text)

        if not translated:
            await interaction.followup.send("Sorry, I couldn't translate that.")
            return

        embed = translation_embed(interaction.guild, translated, language)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Translate(bot))
