import json
import time
import os

import discord
from discord.ext import commands, tasks
from discord import app_commands

from config import settings

DATA_PATH = "data/suggestions.json"


def load_suggestions():
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_suggestions(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("SUGGESTIONS COG INITIALIZED", flush=True)

    async def cog_load(self):
        if not self.check_suggestions.is_running():
            self.check_suggestions.start()

    async def cog_unload(self):
        self.check_suggestions.cancel()

    @app_commands.command(name="suggest", description="Send a suggestion")
    @app_commands.describe(suggestion="Your suggestion")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        member_role_ids = {role.id for role in getattr(interaction.user, "roles", [])}

        if member_role_ids & set(settings.SUGGESTION_BLACKLISTED_ROLE_IDS):
            await interaction.response.send_message(
                "You cannot submit suggestions.",
                ephemeral=True
            )
            return

        if not settings.SUGGESTION_CHANNEL_ID:
            await interaction.response.send_message(
                "Suggestion channel isn't configured yet.",
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(settings.SUGGESTION_CHANNEL_ID)

        if not channel:
            await interaction.response.send_message(
                "Suggestion channel not found.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Suggestion",
            description=suggestion,
            color=0x000000
        )

        embed.add_field(
            name="Suggested By",
            value=interaction.user.mention,
            inline=False
        )

        icon = None
        if interaction.guild and interaction.guild.icon:
            icon = interaction.guild.icon.url

        embed.set_footer(
            text=f"{interaction.guild}",
            icon_url=icon
        )

        message = await channel.send(embed=embed)

        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")

        suggestions = load_suggestions()

        suggestions.append({
            "message_id": message.id,
            "channel_id": channel.id,
            "end_time": int(time.time()) + settings.SUGGESTION_DURATION_SECONDS,
            "ended": False
        })

        save_suggestions(suggestions)

        await interaction.response.send_message(
            "Suggestion sent!",
            ephemeral=True
        )

    @tasks.loop(minutes=1)
    async def check_suggestions(self):
        suggestions = load_suggestions()
        changed = False

        for suggestion in suggestions:
            if suggestion["ended"]:
                continue

            if time.time() < suggestion["end_time"]:
                continue

            try:
                channel = self.bot.get_channel(suggestion["channel_id"])

                if not channel:
                    continue

                message = await channel.fetch_message(suggestion["message_id"])

                up_voters = []
                down_voters = []

                for reaction in message.reactions:
                    if str(reaction.emoji) == "⬆️":
                        async for user in reaction.users():
                            if not user.bot:
                                up_voters.append(user.mention)

                    elif str(reaction.emoji) == "⬇️":
                        async for user in reaction.users():
                            if not user.bot:
                                down_voters.append(user.mention)

                upvotes = len(up_voters)
                downvotes = len(down_voters)
                total = upvotes + downvotes

                if total > 0:
                    up_percent = round((upvotes / total) * 100)
                    down_percent = round((downvotes / total) * 100)
                else:
                    up_percent = 0
                    down_percent = 0

                embed = message.embeds[0]

                embed.add_field(
                    name="Voting Ended",
                    value=f"⬆️ {up_percent}%\n⬇️ {down_percent}%",
                    inline=False
                )

                await message.edit(embed=embed)

                log_channel = None
                if settings.SUGGESTION_LOG_CHANNEL_ID:
                    log_channel = self.bot.get_channel(settings.SUGGESTION_LOG_CHANNEL_ID)

                if log_channel:
                    log_embed = discord.Embed(
                        title="Suggestion Vote Results",
                        color=0x000000
                    )

                    log_embed.add_field(
                        name="Suggestion",
                        value=message.embeds[0].description,
                        inline=False
                    )

                    log_embed.add_field(
                        name="⬆️ Upvoters",
                        value="\n".join(up_voters) if up_voters else "None",
                        inline=False
                    )

                    log_embed.add_field(
                        name="⬇️ Downvoters",
                        value="\n".join(down_voters) if down_voters else "None",
                        inline=False
                    )

                    log_embed.add_field(
                        name="Results",
                        value=f"⬆️ {up_percent}% ({upvotes})\n⬇️ {down_percent}% ({downvotes})",
                        inline=False
                    )

                    await log_channel.send(embed=log_embed)

                suggestion["ended"] = True
                changed = True

            except Exception as e:
                print("Suggestion error:", e, flush=True)

        if changed:
            save_suggestions(suggestions)

    @check_suggestions.before_loop
    async def before_check_suggestions(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Suggestions(bot))