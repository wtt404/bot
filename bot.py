import discord
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_text(url):
        try:
                # First normalize link
                        url = url.replace("x.com", "twitter.com").replace("fxtwitter.com", "twitter.com")

                                # Then convert to API link (only once)
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

        if "twitter.com" in url or "x.com" in url or "fxtwitter.com" in url:
            text = get_text(url)
            translated = translate(text)

            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.channel.send(embed=embed)
            else:
                print("No translation sent")

            return

client.run(os.environ["DISCORD_TOKEN"])
