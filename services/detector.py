import re

from config import settings
from models.detected import DetectedContent

X_PATTERN = re.compile(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/\S+")
TELEGRAM_PATTERN = re.compile(r"https?://t\.me/\S+")

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

    return None