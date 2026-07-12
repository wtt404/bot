import os
from dotenv import load_dotenv

from . import settings

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")