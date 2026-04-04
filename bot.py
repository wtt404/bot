import discord
from discord.ext import commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

# Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Functions ---
def fix_url(url):
    return url.replace("twitter.com", "fxtwitter.com").replace("x.com", "fxtwitter.com")

def get_text(url):
    try:
        api = url.replace("twitter.com", "api.fxtwitter.com").replace("x.com", "api.fxtwitter.com")
        data = requests.get(api).json()
        return data.get("tweet", {}).get("text", "")
    except:
        return ""

def translate(text):
    try:
        if text and detect(text) != "en":
            return GoogleTranslator(source="auto", target="en").translate(text)
        else:
            return None
    except:
        return None

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or message.author == bot.user:
        return

    urls = list(set(re.findall(r"(https?://\S+)", message.content)))

    for url in urls:
        if "fxtwitter.com" in url:
            continue
        if "twitter.com" in url or "x.com" in url:
            fixed = fix_url(url)
            text = get_text(url)
            translated = translate(text)

            # Send translation if needed
            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.channel.send(embed=embed)

            # Send the fxtwitter link separately
            await message.channel.send(fixed)

            return  # stop after first valid link

    await bot.process_commands(message)

# --- Commands restricted to Staff role ---
@bot.command()
@commands.has_role("Staff", "Mod", "Admin")
async def say(ctx, *, text):
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(text)

@bot.command()
@commands.has_role("Staff", "Mod", "Admin")
async def setstatus(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"Status updated to: {text}")

@bot.command()
@commands.has_role("Staff", "Mod", "Admin")
async def online(ctx):
    await bot.change_presence(status=discord.Status.online)
    await ctx.send("Status set to online")

@bot.command()
@commands.has_role("Staff", "Mod", "Admin")
async def idle(ctx):
    await bot.change_presence(status=discord.Status.idle)
    await ctx.send("Status set to idle")

@bot.command()
@commands.has_role("Staff", "Mod", "Admin")
async def dnd(ctx):
    await bot.change_presence(status=discord.Status.dnd)
    await ctx.send("Status set to DND")

# Ping command available to anyone
@bot.command()
async def ping(ctx):
    await ctx.send("pong")

# --- Handle permission errors ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to use this command.")
    else:
        raise error  # let other errors raise normally

# --- Run bot ---
bot.run(os.environ["DISCORD_TOKEN"])
