import discord
from discord.ext import commands
from discord import app_commands

from services.permissions import has_staff_role


class Staff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("STAFF COG INITIALIZED", flush=True)

    @app_commands.command(name="say", description="Send a message through the bot")
    @app_commands.describe(
        text="Input message",
        channel="Channel to send the message in (optional)"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: discord.TextChannel = None
    ):
        if channel is None:
            channel = interaction.channel

        print("----- /say command -----", flush=True)
        print(f"User: {interaction.user} ({interaction.user.id})", flush=True)
        print(f"From channel: {interaction.channel} ({interaction.channel.id})", flush=True)
        print(f"Target channel: {channel} ({channel.id})", flush=True)
        print(f"Message: {text}", flush=True)
        print("------------------------", flush=True)

        if not has_staff_role(interaction.user):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        try:
            await channel.send(text)
            await interaction.response.send_message("Sent.", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("No access to that channel.", ephemeral=True)

        except discord.HTTPException as e:
            print("Channel send error:", e, flush=True)
            await interaction.response.send_message("Channel error.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Staff(bot))