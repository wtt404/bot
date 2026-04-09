import discord
from discord.ext import commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

# --- Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # IMPORTANT for roles

bot = commands.Bot(command_prefix="+", intents=intents)

translation_enabled = True

# --- CONFIG ---
ROLE_IDS = [1489466078525657220]  # PUT YOUR ROLE ID

# --- Role Check ---
def has_role(ctx):
    if not ctx.guild:
        return False
    user_roles = [role.id for role in ctx.author.roles]
    print("User roles:", user_roles)
    return any(role_id in user_roles for role_id in ROLE_IDS)

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
async def toggle(ctx):
    print("Toggle command triggered")

    if not has_role(ctx):
        await ctx.send("No permission.")
        return

    global translation_enabled
    translation_enabled = not translation_enabled

    status = "ON" if translation_enabled else "OFF"
    await ctx.send(f"Translation is now {status}")

@bot.command()
async def say(ctx, *, text):
    print("Say command triggered")

    if not has_role(ctx):
        await ctx.send("No permission.")
        return

    try:
        await ctx.message.delete()
    except:
        pass

    await ctx.send(text)

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    global translation_enabled

    if message.author.bot:
        return

    print("Message received:", message.content)

    # IMPORTANT: commands must be processed FIRST
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
            chunks = [translated[i:i+4096] for i in range(0, len(translated), 4096)]

            for chunk in chunks:
                embed = discord.Embed(description=chunk, color=0x000000)
                await message.reply(embed=embed)

        return

# --- Run ---
bot.run(os.environ["DISCORD_TOKEN"])
