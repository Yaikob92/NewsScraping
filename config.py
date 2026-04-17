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
    # "example_news_channel",
    # "another_channel",
    # -1001234567890,          # numeric channel ID also works
]

# ─── Scraping Settings ────────────────────────────────────────────────────────
MESSAGES_PER_CHANNEL = 5000        # Max messages to fetch per channel
BATCH_SIZE = 100                   # Messages fetched per API call (chunk_size)
MIN_TEXT_LENGTH = 20               # Skip messages shorter than this (after cleaning)
SKIP_MEDIA_ONLY = True             # Skip messages that are only media (no text)

# ─── Output Settings ─────────────────────────────────────────────────────────
OUTPUT_DIR = "data"                # Directory to save scraped data
OUTPUT_FORMATS = ["jsonl", "csv", "mongodb"]  # Supported: "jsonl", "csv", "json", "mongodb"

# ─── Database Settings ───────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASR_URL")
MONGODB_DB_NAME = "telegram_news"
MONGODB_COLLECTION = "messages"
