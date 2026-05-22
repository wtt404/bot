import html
import sqlite3
import time
from discord.ext import tasks
import discord
from discord.ext import commands
from discord import app_commands
import re
import requests
from deep_translator import GoogleTranslator
from langdetect import detect
import os
import asyncio

LANG_NAMES = {
    "ar": "Arabic",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "tr": "Turkish",
    "ru": "Russian",
    "it": "Italian",
    "pt": "Portuguese",
    "fa": "Persian",
    "ur": "Urdu",
    "id": "Indonesian",
    "hi": "Hindi",
    "bn": "Bengali",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "he": "Hebrew",
    "uk": "Ukrainian"
}

# --- Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

translation_enabled = True

# --- CONFIG ---
ROLE_IDS = [1280015405846364171, 1280015168792694838, 1280014871773315103, 1489466078525657220, 1489777324873355364]  # PUT YOUR ROLE ID
SUGGESTION_CHANNEL_ID = 1507404682849681408
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
            import html
            text = html.unescape(text) 
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
        lang_name = LANG_NAMES.get(lang, lang.upper())
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

# --- Suggestions ---

DB_FILE = "suggestions.db"


# -------------------------
# DATABASE
# -------------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        message_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        guild_id INTEGER,
        author_id INTEGER,
        suggestion TEXT,
        created_at TEXT,
        closed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        message_id INTEGER,
        user_id INTEGER,
        vote_type TEXT,
        PRIMARY KEY(message_id, user_id)
    )
    """)

    conn.commit()
    conn.close()


def add_suggestion(
    message_id,
    channel_id,
    guild_id,
    author_id,
    suggestion
):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    INSERT INTO suggestions (
        message_id,
        channel_id,
        guild_id,
        author_id,
        suggestion,
        created_at,
        closed
    )
    VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        message_id,
        channel_id,
        guild_id,
        author_id,
        suggestion,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_vote_counts(message_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    SELECT COUNT(*)
    FROM votes
    WHERE message_id = ?
    AND vote_type = 'up'
    """, (message_id,))
    upvotes = c.fetchone()[0]

    c.execute("""
    SELECT COUNT(*)
    FROM votes
    WHERE message_id = ?
    AND vote_type = 'down'
    """, (message_id,))
    downvotes = c.fetchone()[0]

    conn.close()

    return upvotes, downvotes


def get_user_vote(message_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    SELECT vote_type
    FROM votes
    WHERE message_id = ?
    AND user_id = ?
    """, (message_id, user_id))

    row = c.fetchone()

    conn.close()

    return row[0] if row else None


def set_vote(message_id, user_id, vote_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO votes (
        message_id,
        user_id,
        vote_type
    )
    VALUES (?, ?, ?)
    """, (message_id, user_id, vote_type))

    conn.commit()
    conn.close()


def get_open_suggestions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    SELECT *
    FROM suggestions
    WHERE closed = 0
    """)

    rows = c.fetchall()

    conn.close()

    return rows


def close_suggestion(message_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    UPDATE suggestions
    SET closed = 1
    WHERE message_id = ?
    """, (message_id,))

    conn.commit()
    conn.close()


# -------------------------
# VIEW
# -------------------------

class SuggestionView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def handle_vote(
        self,
        interaction: discord.Interaction,
        vote_type: str
    ):

        message_id = interaction.message.id
        user_id = interaction.user.id

        current_vote = get_user_vote(
            message_id,
            user_id
        )

        if current_vote == vote_type:

            await interaction.response.send_message(
                "You already voted that.",
                ephemeral=True
            )
            return

        set_vote(
            message_id,
            user_id,
            vote_type
        )

        upvotes, downvotes = get_vote_counts(message_id)

        if not interaction.message.embeds:
            return

        old_embed = interaction.message.embeds[0]

        embed = discord.Embed(
            title=old_embed.title,
            description=old_embed.description,
            color=old_embed.color
        )

        for field in old_embed.fields:
            if field.name not in ["👍 Upvotes", "👎 Downvotes"]:
                embed.add_field(
                    name=field.name,
                    value=field.value,
                    inline=field.inline
                )

        embed.add_field(
            name="👍 Upvotes",
            value=str(upvotes),
            inline=True
        )

        embed.add_field(
            name="👎 Downvotes",
            value=str(downvotes),
            inline=True
        )

        embed.set_footer(
            text=old_embed.footer.text,
            icon_url=old_embed.footer.icon_url
        )

        await interaction.message.edit(
            embed=embed,
            view=self
        )

        await interaction.response.send_message(
            f"Vote registered: {'👍' if vote_type == 'up' else '👎'}",
            ephemeral=True
        )

    @discord.ui.button(
        label="👍",
        style=discord.ButtonStyle.green,
        custom_id="suggest_upvote"
    )
    async def upvote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.handle_vote(interaction, "up")

    @discord.ui.button(
        label="👎",
        style=discord.ButtonStyle.red,
        custom_id="suggest_downvote"
    )
    async def downvote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.handle_vote(interaction, "down")


# -------------------------
# SLASH COMMAND
# -------------------------

@bot.tree.command(
    name="suggest",
    description="Send a suggestion"
)
@app_commands.describe(
    suggestion="Your suggestion"
)
async def suggest(
    interaction: discord.Interaction,
    suggestion: str
):

    suggestion_channel = bot.get_channel(
        SUGGESTION_CHANNEL_ID
    )

    if suggestion_channel is None:
        await interaction.response.send_message(
            "Suggestion channel not found.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="New Suggestion",
        description=suggestion,
        color=0x40B8DB
    )

    embed.add_field(
        name="Suggested by",
        value=f"{interaction.user.mention} ({interaction.user})",
        inline=False
    )

    embed.add_field(
        name="👍 Upvotes",
        value="0",
        inline=True
    )

    embed.add_field(
        name="👎 Downvotes",
        value="0",
        inline=True
    )

    icon = None

    if interaction.guild and interaction.guild.icon:
        icon = interaction.guild.icon.url

    embed.set_footer(
        text=f"{interaction.guild}",
        icon_url=icon
    )

    msg = await suggestion_channel.send(
        embed=embed,
        view=SuggestionView()
    )

    add_suggestion(
        msg.id,
        msg.channel.id,
        interaction.guild.id,
        interaction.user.id,
        suggestion
    )

    await interaction.response.send_message(
        "Suggestion sent!",
        ephemeral=True
    )


# -------------------------
# AUTO CLOSE LOOP
# -------------------------

@tasks.loop(minutes=5)
async def check_suggestions():

    suggestions = get_open_suggestions()

    for s in suggestions:

        (
            message_id,
            channel_id,
            guild_id,
            author_id,
            suggestion,
            created_at,
            closed
        ) = s

        created_dt = datetime.fromisoformat(created_at)

        if datetime.utcnow() >= created_dt + timedelta(days=2):

            try:

                channel = bot.get_channel(channel_id)

                if channel is None:
                    continue

                message = await channel.fetch_message(message_id)

                upvotes, downvotes = get_vote_counts(message_id)

                total = upvotes + downvotes

                if total == 0:
                    up_percent = 0
                    down_percent = 0
                else:
                    up_percent = round(
                        (upvotes / total) * 100,
                        1
                    )

                    down_percent = round(
                        (downvotes / total) * 100,
                        1
                    )

                old_embed = message.embeds[0]

                embed = discord.Embed(
                    title=old_embed.title,
                    description=old_embed.description,
                    color=discord.Color.red()
                )

                for field in old_embed.fields:
                    if field.name not in [
                        "Voting Closed"
                    ]:
                        embed.add_field(
                            name=field.name,
                            value=field.value,
                            inline=field.inline
                        )

                embed.add_field(
                    name="Voting Closed",
                    value=(
                        f"👍 {upvotes} ({up_percent}%)\n"
                        f"👎 {downvotes} ({down_percent}%)"
                    ),
                    inline=False
                )

                embed.set_footer(
                    text=old_embed.footer.text,
                    icon_url=old_embed.footer.icon_url
                )

                await message.edit(
                    embed=embed,
                    view=None
                )

                close_suggestion(message_id)

            except Exception as e:
                print(
                    f"Suggestion close error: {e}"
                )

# --- NEW SLASH COMMAND ---
@bot.tree.command(name="translate", description="Translate text to English")
@app_commands.describe(text="Text to translate")
async def translate_cmd(interaction: discord.Interaction, text: str):
    try:

        clean = re.sub(r"[^\w\s]", "", text)
        try:
            lang = detect(clean)
        except:
            lang = "unknown"

        lang_name = LANG_NAMES.get(lang, lang.upper())
        
        if lang == "en":
            await interaction.response.send_message(
                "Text is already in English.",
                ephemeral=True
            )
    
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        translated = html.unescape(translated)
        
        chunks = [translated[i:i+4096] for i in range(0, len(translated), 4096)]

        for chunk in chunks:
            embed = discord.Embed(description=chunk, color=0x40B8DB)
            icon = None
        if interaction.guild and interaction.guild.icon:
            icon = interaction.guild.icon.url
            embed.set_footer(
            text=f"Translated from {lang_name}",
             icon_url=icon
                )

            await interaction.response.send_message(embed=embed)

    except Exception as e:
        print("Translate command error:", e)
        await interaction.response.send_message("Translation failed.", ephemeral=True)

@bot.tree.command(name="say", description="Send a message through the bot")
@app_commands.describe(
    text="Input message",
    channel="Channel to send the message in (optional)"
)
async def say_slash(interaction: discord.Interaction, text: str, channel: discord.TextChannel = None):
    if channel is None:
        channel = interaction.channel
        
    print("----- /say command -----")
    print(f"User: {interaction.user} ({interaction.user.id})")
    print(f"From channel: {interaction.channel} ({interaction.channel.id})")
    print(f"Target channel: {channel} ({channel.id})")
    print(f"Message: {text}")
    print("------------------------")

    user_roles = [role.id for role in interaction.user.roles]
    if not any(role_id in user_roles for role_id in ROLE_IDS):
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

        
        if channel is not None and not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Invalid channel type.", ephemeral=True)
            return

    try:
        await channel.send(text)
        await interaction.response.send_message("Sent.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("No access to that channel.", ephemeral=True)
        return

    except discord.HTTPException as e:
        print("Channel send error:", e)
        await interaction.response.send_message("Channel error.", ephemeral=True)
        return

# --- Events ---
@bot.event
async def on_ready():
    init_db()

    bot.add_view(SuggestionView())

    if not check_suggestions.is_running():
        check_suggestions.start()
    
    await bot.tree.sync()  # sync slash command
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    global translation_enabled

    if message.author.bot:
        return

    if message.guild:
        print(f"[SERVER] {message.guild} | #{message.channel} | {message.author}: {message.content}")
    else:
        print(f"[DM] {message.author}: {message.content}")

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

        clean = re.sub(r"[^\w\s]", "", text)
        
        try:
            lang = detect(clean)
        except: 
            lang = "unknown"
        
        lang_name = LANG_NAMES.get(lang, lang.upper())
        
        translated = translate(text)

        if translated:
            chunks = [translated[i:i+4096] for i in range(0, len(translated), 4096)]
            for chunk in chunks:
                embed = discord.Embed(description=chunk, color=0x40B8DB)
                icon = None
            if message.guild and message.guild.icon:
               icon = message.guild.icon.url
               embed.set_footer(
               text=f"Translated from {lang_name}",
                icon_url=icon
                   )
                
            await message.reply(embed=embed)
        return

# --- Run ---
bot.run(os.environ["DISCORD_TOKEN"])
