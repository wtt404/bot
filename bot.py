import discord
from discord.ext import commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
        lang = detect(text)
        if lang != "en":
            return GoogleTranslator(source="auto", target="en").translate(text)
        else:
            return None  # already English
    except:
        return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    urls = re.findall(r"(https?://\S+)", message.content)

    for url in urls:
        if "twitter.com" in url or "x.com" in url:
            fixed = fix_url(url)
            text = get_text(url)
            translated = translate(text)

            # only send embed if translation exists
            if translated:
                embed = discord.Embed(description=translated, color=0x000000)
                await message.channel.send(embed=embed)

            # always send the tweet link
            await message.channel.send(fixed)

    await bot.process_commands(message)

bot.run("MTE3NTkxMzMxMzU5NTU2MDAyOA.Gdu-cJ.gTO-PC3GRg3MsXyd7j2njKcUalkcv38VWP5y4w")
