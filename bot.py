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

# Functions
def get_text(url):
    try:
        api = url.replace("twitter.com", "api.fxtwitter.com") \
                 .replace("x.com", "api.fxtwitter.com") \
                 .replace("fxtwitter.com", "api.fxtwitter.com")
        data = requests.get(api).json()
        return data.get("tweet", {}).get("text", "")
    except:
        return ""

def translate(text):
    try:
        if text and detect(text) != "en":
            return GoogleTranslator(source="auto", target="en").translate(text)
    except:
        return None
    return None

# Events
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    urls = list(set(re.findall(r"(https?://\S+)", message.content)))

    for url in urls:
        if "twitter.com" in url or "x.com" in url or "fxtwitter.com" in url:
            text = get_text(url)
            translated = translate(text)

            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.channel.send(embed=embed)

            return

# Run
client.run(os.environ["DISCORD_TOKEN"]) 
