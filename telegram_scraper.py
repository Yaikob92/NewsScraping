"""
Telegram Channel Scraper
Uses Telethon to connect to the Telegram API and scrape messages
from specified news channels.
"""

import logging
from typing import AsyncGenerator

from telethon import TelegramClient
from telethon.tl.types import Channel, Message

import config

logger = logging.getLogger(__name__)


class TelegramScraper:
    """Async Telegram channel scraper powered by Telethon."""

    def __init__(self):
        self.client = TelegramClient(
            config.SESSION_NAME,
            int(config.API_ID),
            config.API_HASH,
        )

    # ── Connection ────────────────────────────────────────────────────────
    async def connect(self) -> None:
        """Start the client and authenticate (interactive on first run)."""
        await self.client.start(phone=config.PHONE_NUMBER)
        me = await self.client.get_me()
        logger.info(f"Logged in as {me.first_name} (id={me.id})")

    async def disconnect(self) -> None:
        await self.client.disconnect()

    # ── Channel info ──────────────────────────────────────────────────────
    async def resolve_channel(self, channel_ref) -> Channel | None:
        """Resolve a channel username or ID to a Channel entity."""
        try:
            entity = await self.client.get_entity(channel_ref)
            if isinstance(entity, Channel):
                logger.info(f"Resolved channel: {entity.title} (id={entity.id})")
                return entity
            logger.warning(f"{channel_ref} is not a channel, skipping.")
            return None
        except Exception as e:
            logger.error(f"Could not resolve {channel_ref}: {e}")
            return None

    # ── Message iteration ─────────────────────────────────────────────────
    async def iter_messages(
        self,
        channel: Channel,
        limit: int = config.MESSAGES_PER_CHANNEL,
    ) -> AsyncGenerator[dict, None]:
        """
        Yields raw message dicts from the given channel.
        Each dict contains: id, date, text, views, forwards, channel_title, channel_id.
        """
        count = 0
        async for msg in self.client.iter_messages(
            channel,
            limit=limit,
            chunk_size=config.BATCH_SIZE,
        ):
            if not isinstance(msg, Message):
                continue

            # Skip media-only posts if configured
            if config.SKIP_MEDIA_ONLY and not msg.text:
                continue

            count += 1
            yield {
                "message_id": msg.id,
                "channel_id": channel.id,
                "channel_title": channel.title,
                "date": msg.date.isoformat() if msg.date else None,
                "raw_text": msg.text or "",
                "views": msg.views or 0,
                "forwards": msg.forwards or 0,
            }

            if count % 500 == 0:
                logger.info(f"  … fetched {count} messages from {channel.title}")

        logger.info(f"Fetched {count} messages total from {channel.title}")

    # ── Convenience: scrape all configured channels ───────────────────────
    async def scrape_all(self) -> AsyncGenerator[dict, None]:
        """Iterate over every configured channel and yield message dicts."""
        for ch_ref in config.CHANNELS:
            channel = await self.resolve_channel(ch_ref)
            if channel is None:
                continue
            async for msg_dict in self.iter_messages(channel):
                yield msg_dict
