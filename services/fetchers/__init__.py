from services.fetchers.x import XFetcher
from services.fetchers.telegram import TelegramFetcher

FETCHERS = {
    "x": XFetcher(),
    "telegram": TelegramFetcher(),
}