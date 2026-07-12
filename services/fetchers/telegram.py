import re
import aiohttp
from bs4 import BeautifulSoup

from models.post import Post, Media
from services.fetchers.base import Fetcher

URL_PATTERN = re.compile(r"t\.me/(?:s/)?([A-Za-z0-9_]+)/(\d+)")
BG_IMAGE_PATTERN = re.compile(r"background-image:url\('([^']+)'\)")


class TelegramFetcher(Fetcher):
    async def fetch(self, url: str) -> Post:
        match = URL_PATTERN.search(url)

        if not match:
            raise RuntimeError(
                "Unsupported Telegram URL (private/invite-only channels aren't supported)"
            )

        channel, msg_id = match.groups()
        embed_url = f"https://t.me/{channel}/{msg_id}?embed=1&mode=tme"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Telegram returned status {resp.status}")

                body = await resp.text()

        if "tgme_widget_message" not in body:
            raise RuntimeError("Telegram post not found or channel is private")

        soup = BeautifulSoup(body, "html.parser")

        target = f"{channel}/{msg_id}".lower()
        message_el = None

        for candidate in soup.select("[data-post]"):
            if candidate.get("data-post", "").lower() == target:
                message_el = candidate
                break

        if message_el is None:
            message_el = soup  # fallback: best effort if markup changes

        # Strip any quoted/replied-to message block first, so its text and
        # media can never be mistaken for the actual post's own content.
        for reply_block in message_el.select(".tgme_widget_message_reply"):
            reply_block.decompose()

        text_el = message_el.select_one(".tgme_widget_message_text")

        text = ""
        if text_el:
            for br in text_el.find_all("br"):
                br.replace_with("\n")
            text = text_el.get_text().strip()

        seen = set()
        media = []

        # Photos are rendered as an element with a background-image inline
        # style. Match on "class contains" rather than an exact class
        # attribute, since Telegram often appends extra classes.
        for el in message_el.select('[class*="tgme_widget_message_photo_wrap"]'):
            style = el.get("style", "")
            m = BG_IMAGE_PATTERN.search(style)

            if not m:
                continue

            photo_url = m.group(1).replace("&amp;", "&")

            if photo_url in seen:
                continue

            seen.add(photo_url)
            media.append(Media(url=photo_url, type="image"))

        # Videos: only recoverable when Telegram's lightweight preview embeds
        # a direct <video src>. Larger/longer videos are intentionally not
        # embedded by Telegram here and can't be recovered without the
        # Telegram API/app - those will just come through with no video media.
        for el in message_el.select("video"):
            src = el.get("src")

            if not src:
                source = el.find("source")
                src = source.get("src") if source else None

            if not src or src in seen:
                continue

            seen.add(src)
            media.append(Media(url=src.replace("&amp;", "&"), type="video"))

        return Post(platform="telegram", text=text, media=media)