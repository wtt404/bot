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

# --- Functions ---
def get_text(url):
    try:
        # normalize link to twitter.com
        url = url.replace("x.com", "twitter.com") \
                 .replace("fxtwitter.com", "twitter.com") \
                 .replace("fixupx.com", "twitter.com")

        # convert to API link
        api = url.replace("twitter.com", "api.fxtwitter.com")

        print("Fetching:", api)

        r = requests.get(api)
        data = r.json()

        text = data.get("tweet", {}).get("text", "")
        print("Extracted text:", text)

        return text

    except Exception as e:
        print("ERROR get_text:", e)
        return ""

def translate(text):
    try:
        if not text:
            return None

        lang = detect(text)
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

        if any(domain in url for domain in ["twitter.com", "x.com", "fxtwitter.com", "fixupx.com"]):
            text = get_text(url)
            translated = translate(text)

            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.reply(embed=embed)
            else:
                print("No translation sent")

            return

# --- Run ---
client.run(os.environ["DISCORD_TOKEN"])
