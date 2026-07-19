import os
from dotenv import load_dotenv

from . import settings

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
