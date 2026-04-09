import discord
from discord.ext import commands
from discord import app_commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os

# --- Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)
tree = app_commands.CommandTree(bot)

translation_enabled = True

# --- CONFIG ---
ROLE_IDS = [123456789012345678]  # PUT YOUR ROLE ID

# --- Role Check ---
def has_role(ctx):
    if not ctx.guild:
        print("Not in a guild")
        return False

    user_roles = [role.id for role in ctx.author.roles]
    print(f"User: {ctx.author}, Roles: {user_roles}")
    check = any(role_id in user_roles for role_id in ROLE_IDS)
    print(f"Role check passed: {check}")
    return check

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
    except Exception as e:
        print("Error getting Twitter text:", e)
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
    except Exception as e:
        print("Error getting Telegram text:", e)
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
    except Exception as e:
        print("Translation error:", e)
        return None
    return None

# --- PREFIX COMMANDS ---
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
    except Exception as e:
        print("Failed to delete command:", e)

    await ctx.send(text)

# --- NEW SLASH COMMAND ---
@tree.command(name="translate", description="Translate text to English")
@app_commands.describe(text="Text to translate")
async def translate_cmd(interaction: discord.Interaction, text: str):
    try:
        user_roles = [role.id for role in interaction.user.roles]

        if not any(role_id in user_roles for role_id in ROLE_IDS):
            await interaction.response.send_message(
                "You do not have permission to use this command.",
                ephemeral=True
            )
            return

        clean = re.sub(r"[^\w\s]", "", text)
        lang = detect(clean)

        if lang == "en":
            await interaction.response.send_message(
                "Text is already in English.",
                ephemeral=True
            )
            return

        translated = GoogleTranslator(source="auto", target="en").translate(text)

        chunks = [translated[i:i+4096] for i in range(0, len(translated), 4096)]

        await interaction.response.send_message("Translation:", ephemeral=True)

        for chunk in chunks:
            embed = discord.Embed(description=chunk, color=0x000000)
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        print("Translate command error:", e)
        await interaction.response.send_message("Translation failed.", ephemeral=True)

# --- Events ---
@bot.event
async def on_ready():
    await tree.sync()  # sync slash command
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    global translation_enabled

    if message.author.bot:
        return

    print(f"Message received: {message.content} (from {message.author})")

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
