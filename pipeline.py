"""
Main Pipeline — Telegram News Scraping & Cleaning
Orchestrates:
  1. Connecting to Telegram
  2. Scraping news from configured channels
  3. Cleaning each item
  4. Exporting cleaned data to ML-ready formats

Usage
─────
  python pipeline.py                  # scrape all channels in config
  python pipeline.py --channel @chan  # scrape a single channel (override)
  python pipeline.py --limit 1000    # override message limit per channel
"""

import argparse
import asyncio
import logging
import sys
import time

import config
from telegram_scraper import TelegramScraper
from telegram_cleaner import clean_telegram_message
from data_exporter import create_exporters

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


# ── Pipeline ──────────────────────────────────────────────────────────────────
async def run_pipeline(
    channels: list | None = None,
    limit: int | None = None,
    listen: bool = False,
) -> None:
    scraper = TelegramScraper()

    # Override config at runtime if needed
    if channels:
        config.CHANNELS = channels
    if limit:
        config.MESSAGES_PER_CHANNEL = limit

    if not config.CHANNELS:
        logger.error(
            "No channels configured! Add channels to config.py or use --channel."
        )
        sys.exit(1)

    exporters = create_exporters()
    total = 0
    skipped = 0
    errors = 0
    start = time.time()

    try:
        await scraper.connect()

        async def process_msg(raw_msg: dict):
            nonlocal total, skipped, errors
            try:
                # Clean the text
                cleaned = clean_telegram_message(raw_msg["text"])
                clean_text = cleaned["news_text"]

                # Skip very short / empty results
                if len(clean_text) < config.MIN_TEXT_LENGTH:
                    skipped += 1
                    return

                # Merge everything together!
                record = {
                    "message_id": raw_msg["message_id"],
                    "raw_text": raw_msg["text"],
                    "news_text": clean_text,
                    "label": None,
                    "date": raw_msg["date"],
                    "views": raw_msg["views"],
                    "forwards": raw_msg["forwards"],
                    "repost": raw_msg["repost"],
                    "likes": raw_msg["likes"],
                    "like_count": raw_msg["like_count"],
                    "comment_count": raw_msg["comment_count"],
                    "media_url": raw_msg.get("media_url"),
                    "channel_profile_picture": raw_msg["channel"].get("profile_photo"),
                    "channel_username": raw_msg["channel"].get("username"),
                    "channel_id": raw_msg["channel"].get("id"),
                    "channel_name": raw_msg["channel"].get("name"),
                    "channel": raw_msg["channel"],
                    "metadata": raw_msg["metadata"],
                }

                # Write to all exporters
                for exp in exporters:
                    exp.write(record)

                total += 1
                if total % 10 == 0 or listen:
                    logger.info(f"✓ {total} records saved so far …")

            except Exception as e:
                errors += 1
                msg_id = raw_msg.get("message_id", "?")
                logger.warning(f"Error processing message {msg_id}: {e}")

        if listen:
            logger.info("Starting pipeline in LISTEN mode (waiting for new messages)...")
            await scraper.listen_for_new_messages(process_msg)
        else:
            logger.info("Starting pipeline in BATCH mode (fetching historical messages)...")
            async for raw_msg in scraper.scrape_all():
                await process_msg(raw_msg)

    except KeyboardInterrupt:
        logger.warning("Interrupted by user — saving collected data …")
    finally:
        for exp in exporters:
            exp.close()
        await scraper.disconnect()

    elapsed = time.time() - start
    logger.info("─" * 60)
    logger.info(f"Done!  {total} records saved, {skipped} skipped, {errors} errors")
    logger.info(f"Time elapsed: {elapsed:.1f}s")
    logger.info("─" * 60)

def main():
    parser = argparse.ArgumentParser(
        description="Telegram News Scraping Pipeline for ML Training Data"
    )
    parser.add_argument(
        "--channel",
        action="append",
        default=None,
        help="Telegram channel username or ID (can be used multiple times)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override max messages per channel",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Run continuously and listen for new messages instantly",
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(channels=args.channel, limit=args.limit, listen=args.listen))


if __name__ == "__main__":
    main()
