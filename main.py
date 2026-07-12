import os
import asyncio

import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from services.browser import start_browser, stop_browser


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="-",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    print("=" * 40)
    print(f"Logged in as {bot.user}")
    print(f"Bot object id: {id(bot)}")
    print("=" * 40)
    for name, command in bot.all_commands.items():
        print(name, id(command), flush=True)
    print(bot.extensions.keys(), flush=True)

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)", flush=True)
    except Exception as e:
        print(f"Slash command sync failed: {e}", flush=True)


async def load_cogs():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load_cogs()
        await start_browser()
       
        try:
           await bot.start(DISCORD_TOKEN)
        finally:
           await stop_browser()


if __name__ == "__main__":
    asyncio.run(main())