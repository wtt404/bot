import discord
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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

# --- Events ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
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
            # MAXIMIZE Discord limit (4096 safe margin)
            max_len = 4096
            chunks = [translated[i:i+max_len] for i in range(0, len(translated), max_len)]

            for chunk in chunks:
                embed = discord.Embed(
                    description=chunk,
                    color=0x000000
                )
                await message.reply(embed=embed)

        return

client.run(os.environ["DISCORD_TOKEN"])
