import discord
from discord.ext import commands
from discord import app_commands

from ai.agent import ai
from services.ocr import ocr_image


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


class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("AI COG INITIALIZED", flush=True)


    @commands.command(name="ai")
    async def ai(self, ctx, *, prompt: str = None):
        await ctx.typing()
        print(f"COMMAND {ctx.command} | message={ctx.message.id}", flush=True)

        print("=" * 50)
        print("Ai COMMAND")
        print("=" * 50)

        image_attachments = [
            a for a in ctx.message.attachments
            if a.content_type and a.content_type.startswith("image/")
        ]

        if not prompt and not image_attachments:
            await ctx.send("Give me a question, or attach an image for me to read.")
            return

        ocr_text_parts = []

        for attachment in image_attachments:
            image_bytes = await attachment.read()
            text = await ocr_image(image_bytes, filename=attachment.filename)

            if text:
                ocr_text_parts.append(text)

        if image_attachments and not ocr_text_parts:
            await ctx.send("I couldn't read any text from that image.")
            return

        full_prompt = prompt or "Translate the text found in the attached image."

        if ocr_text_parts:
            full_prompt += "\n\nText found in attached image(s):\n" + "\n---\n".join(ocr_text_parts)

        try:
            reply = await ai(full_prompt.strip())
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"-ai command failed: {e}", flush=True)
            await ctx.send(f"Something went wrong: {e}")
            return

        if not reply:
            await ctx.send("Sorry, I couldn't come up with a response.")
            return

        if len(reply) > 2000:
            reply = reply[:1990] + "..."

        await ctx.send(reply)

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
    await bot.add_cog(AI(bot))