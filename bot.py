import discord
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

# Setup
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

        print("Fetching Twitter:", api)

        r = requests.get(api)
        data = r.json()

        return data.get("tweet", {}).get("text", "")

    except Exception as e:
        print("ERROR Twitter:", e)
        return ""

# --- Telegram ---
def get_telegram_text(url):
    try:
        print("Fetching Telegram:", url)

        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text

        # Better extraction
        match = re.search(r'property="og:description" content="([^"]+)"', html)

        if match:
            text = match.group(1)
            text = text.replace("&quot;", "\"").replace("&amp;", "&")
            print("Telegram text:", text)
            return text

        print("No Telegram text found")
        return ""

    except Exception as e:
        print("ERROR Telegram:", e)
        return ""

# --- Translate ---
def translate(text):
    try:
        if not text:
            print("No text to translate")
            return None

        clean = re.sub(r"[^\w\s]", "", text)

        lang = detect(clean)
        print("Detected language:", lang)

        if lang != "en":
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            print("Translated:", translated)
            return translated

    except Exception as e:
        print("ERROR translate:", e)

    return None

# --- Events ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    print("Message:", message.content)

    # STRONG URL DETECTION
    urls = re.findall(r"https?://[^\s]+", message.content)

    if not urls:
        print("No URLs found")
        return

    for url in urls:
        print("Processing:", url)

        text = ""

        if any(d in url for d in ["twitter.com", "x.com", "fxtwitter.com", "fixupx.com"]):
            text = get_text(url)

        elif "t.me" in url:
            text = get_telegram_text(url)

        else:
            print("Not supported link")
            continue

        translated = translate(text)

        if translated:
            embed = discord.Embed(description=translated, color=0x000000)
            await message.reply(embed=embed)
        else:
            print("Nothing translated")

        return

# Run
client.run(os.environ["DISCORD_TOKEN"]) 
