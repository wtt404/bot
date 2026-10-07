from services.fetchers.x import XFetcher
from services.fetchers.telegram import TelegramFetcher
from services.fetchers.instagram import InstagramFetcher

FETCHERS = {
    "x": XFetcher(),
    "telegram": TelegramFetcher(),
    "instagram": InstagramFetcher(),
}
