import discord
from discord.ext import commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

# Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents)

translation_enabled = True

# --- CONFIG ---
ROLE_IDS = [1477082293184233633,1489466078525657220]  # ← PUT YOUR ROLE IDs

# --- Role Check ---
def has_role(ctx):
    return any(role.id in ROLE_IDS for role in ctx.author.roles)

# --- Twitter ---
def get_text(url):
    try:
        url = url.replace("fixupx.com", "twitter.com").replace("fixup", "")

        if "fxtwitter.com" in url:
            api = url.replace("fxtwitter.com", "api.fxtwitter.com")
        else:
            api = url.replace("twitter.com", "api.fxtwitter.com").replace("x.com", "api.fxtwitter.com")

        r = requests.get(api)
        data = r.json()
        return data.get("tweet", {}).get("text", "")
    except:
        return ""

# --- Telegram ---
def get_telegram_text(url):
    try:
        r = requests.get(url + "?embed=1", headers={"User-Agent": "Mozilla/5.0"})
        html = r.text

        match = re.search(r'class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)
        if match:
            text = re.sub(r"<.*?>", "", match.group(1))
            text = text.replace("&quot;", "\"").replace("&amp;", "&")
            return text
        return ""
    except:
        return ""

# --- Translate ---
def translate(text):
    try:
        if not text:
            return None

        clean = re.sub(r"[^\w\s]", "", text)
        lang = detect(clean)

        if lang != "en":
            return GoogleTranslator(source="auto", target="en").translate(text)
    except:
        return None

    return None

# --- Commands ---
@bot.command()
@commands.check(has_role)
async def toggle(ctx):
    global translation_enabled
    translation_enabled = not translation_enabled

    status = "ON" if translation_enabled else "OFF"
    await ctx.send(f"Translation is now {status}")

@bot.command()
@commands.check(has_role)
async def say(ctx, *, text):
    try:
        await ctx.message.delete()
    except:
        pass

    await ctx.send(text)

# --- Error Handler ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have permission to use this command.")
    else:
        raise error

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    global translation_enabled

    if message.author.bot:
        return

    await bot.process_commands(message)

    if not translation_enabled:
        return

    urls = re.findall(r"https?://[^\s]+", message.content)

    for url in urls:
        text = ""

        if any(d in url for d in ["twitter.com", "x.com", "fxtwitter.com", "fixupx.com"]):
            text = get_text(url)
        elif "t.me" in url:
            text = get_telegram_text(url)

        translated = translate(text)

        if translated:
            max_len = 4096
            chunks = [translated[i:i+max_len] for i in range(0, len(translated), max_len)]

            for chunk in chunks:
                embed = discord.Embed(description=chunk, color=0x000000)
                await message.reply(embed=embed)

        return

# Run
bot.run(os.environ["DISCORD_TOKEN"]) 
