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

# --- Twitter Function ---
def get_text(url):
    try:
        # Fix fixup links
        url = url.replace("fixupx.com", "twitter.com").replace("fixup", "")

        # Build API URL
        if "fxtwitter.com" in url:
            api = url.replace("fxtwitter.com", "api.fxtwitter.com")
        else:
            api = url.replace("twitter.com", "api.fxtwitter.com").replace("x.com", "api.fxtwitter.com")

        print("Fetching Twitter:", api)

        r = requests.get(api)
        data = r.json()

        text = data.get("tweet", {}).get("text", "")
        print("Extracted Twitter text:", text)

        return text

    except Exception as e:
        print("ERROR get_text:", e)
        return ""

# --- Telegram Function ---
def get_telegram_text(url):
    try:
        print("Fetching Telegram:", url)

        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text

        match = re.search(r'<meta property="og:description" content="(.*?)"', html)

        if match:
            text = match.group(1)

            # Fix encoding
            text = text.replace("&quot;", "\"").replace("&amp;", "&")

            print("Telegram text:", text)
            return text

        print("No Telegram text found")
        return ""

    except Exception as e:
        print("ERROR Telegram:", e)
        return ""

# --- Translation ---
def translate(text):
    try:
        if not text or len(text.strip()) < 2:
            print("Text empty or too short")
            return None

        # Clean text for detection
        clean_text = re.sub(r"http\S+|@\S+|#\S+", "", text)
        clean_text = re.sub(r"[^\w\s.,!?]", "", clean_text)

        print("Cleaned text:", clean_text)

        lang = detect(clean_text)
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

    print("Message received:", message.content)

    urls = re.findall(r"(https?://\S+)", message.content)

    for url in urls:
        print("Found URL:", url)

        text = ""

        # Twitter / X / FX / Fixup
        if any(d in url for d in ["twitter.com", "x.com", "fxtwitter.com", "fixupx.com"]):
            text = get_text(url)

        # Telegram
        elif "t.me" in url:
            text = get_telegram_text(url)

        # Translate
        translated = translate(text)

        if translated:
            embed = discord.Embed(description=translated, color=0x000000)
            await message.reply(embed=embed)
        else:
            print("No translation sent")

        return

# Run
client.run(os.environ["DISCORD_TOKEN"])
