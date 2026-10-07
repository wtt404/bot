import re

from config import settings
from models.detected import DetectedContent

X_PATTERN = re.compile(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/\S+")
TELEGRAM_PATTERN = re.compile(r"https?://(?:t\.me|telegram\.dog)/\S+")
INSTAGRAM_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:instagram\.com|instagr\.am)/(?:[A-Za-z0-9_.]+/)?(?:p|reel|reels|tv|share)/\S+"
)


def detect(message: str):
    if settings.AUTO_X:
        x = X_PATTERN.search(message)
        if x:
            return DetectedContent(
                type="x",
                url=x.group()
            )

    if settings.AUTO_TELEGRAM:
        telegram = TELEGRAM_PATTERN.search(message)
        if telegram:
            return DetectedContent(
                type="telegram",
                url=telegram.group()
            )

    if getattr(settings, "AUTO_INSTAGRAM", True):
        instagram = INSTAGRAM_PATTERN.search(message)
        if instagram:
            return DetectedContent(
                type="instagram",
                url=instagram.group()
            )

    return None
