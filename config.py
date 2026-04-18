"""
Configuration for the Telegram Scraping Pipeline.

Credentials are loaded from environment variables (or a .env file).
To get your API credentials:
  1. Go to https://my.telegram.org
  2. Log in with your phone number
  3. Click "API development tools"
  4. Create an application — you'll get api_id and api_hash

Setup:
  cp .env.example .env     # then fill in your real credentials
"""

import os
import sys

from dotenv import load_dotenv

# Load .env file (if present) into the environment
load_dotenv()

# ─── Telegram API Credentials ────────────────────────────────────────────────
API_ID = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")
SESSION_NAME = "scraper_session"

# Quick sanity check on import
if not API_ID or not API_HASH:
    print(
        "⚠️  TELEGRAM_API_ID and TELEGRAM_API_HASH are not set.\n"
        "   Copy .env.example → .env and fill in your credentials.\n"
        "   Or export them as environment variables.",
        file=sys.stderr,
    )

# ─── Channels to Scrape ──────────────────────────────────────────────────────
# Add Telegram channel usernames (without @) or channel IDs.
# Examples of Ethiopian news channels — replace with your targets.
CHANNELS = [
    "@tikvahethiopia",
    "@tikvahethsport",
    "@tikvahethmagazine",
    "@EBCNEWSNOW",
]

# ─── Scraping Settings ────────────────────────────────────────────────────────
MESSAGES_PER_CHANNEL = int(os.getenv("MESSAGES_PER_CHANNEL", "5000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "20"))
SKIP_MEDIA_ONLY = os.getenv("SKIP_MEDIA_ONLY", "True").lower() == "true"

# ─── Output Settings ─────────────────────────────────────────────────────────
OUTPUT_FORMATS = ["mongodb"]  # Only saving to database as requested

# ─── Database Settings ───────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "telegram_news")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "messages")

# ─── Cloudinary Settings ─────────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
