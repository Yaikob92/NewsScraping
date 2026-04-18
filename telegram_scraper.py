"""
Telegram Channel Scraper
Uses Telethon to connect to the Telegram API and scrape messages
from specified news channels.
"""

import logging
from typing import AsyncGenerator

from telethon import TelegramClient, events
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
        """
        # Resolve profile photo once per channel scrape if needed
        profile_url = None
        try:
            from media_handler import upload_to_cloudinary
            photo_bytes = await self.client.download_profile_photo(channel, bytes)
            if photo_bytes:
                profile_url = await upload_to_cloudinary(
                    photo_bytes, 
                    folder="channel_profiles", 
                    public_id=f"channel_{channel.id}"
                )
        except Exception as e:
            logger.warning(f"Could not upload profile photo for {channel.title}: {e}")

        count = 0
        async for msg in self.client.iter_messages(
            channel,
            limit=limit,
        ):
            if not isinstance(msg, Message):
                continue

            formatted_msg = await self._format_message(msg, channel, profile_url)
            if formatted_msg:
                count += 1
                yield formatted_msg

            if count > 0 and count % 500 == 0:
                logger.info(f"  … fetched {count} messages from {channel.title}")

        logger.info(f"Fetched {count} messages total from {channel.title}")

    async def _format_message(self, msg: Message, channel: Channel, profile_url: str | None = None) -> dict | None:
        """Format a Telethon Message into our standard dictionary."""
        # Skip media-only posts if configured
        if config.SKIP_MEDIA_ONLY and not msg.text:
            return None

        has_links = False
        raw_text = msg.text or ""
        if "http" in raw_text or "www." in raw_text or "t.me" in raw_text:
            has_links = True

        # Reactions (Likes)
        like_count = 0
        likes = []
        if msg.reactions:
            for r in msg.reactions.results:
                like_count += r.count
                likes.append({
                    "emoticon": getattr(r.reaction, 'emoticon', str(r.reaction)),
                    "count": r.count
                })

        # Replies (Comments)
        comment_count = 0
        if msg.replies:
            comment_count = getattr(msg.replies, 'replies', 0)

        # Media (Images)
        media_url = None
        if msg.photo:
            try:
                from media_handler import upload_to_cloudinary
                photo_bytes = await self.client.download_media(msg.photo, bytes)
                if photo_bytes:
                    media_url = await upload_to_cloudinary(
                        photo_bytes, 
                        folder="news_media", 
                        public_id=f"msg_{channel.id}_{msg.id}"
                    )
            except Exception as e:
                logger.warning(f"Could not upload media for message {msg.id}: {e}")

        return {
            "message_id": msg.id,
            "text": raw_text,
            "date": msg.date.isoformat() if msg.date else None,
            "views": getattr(msg, "views", 0) or 0,
            "forwards": getattr(msg, "forwards", 0) or 0,
            "repost": getattr(msg, "forwards", 0) or 0,
            "likes": likes,
            "like_count": like_count,
            "comment_count": comment_count,
            "media_url": media_url,
            "channel": {
                "id": channel.id,
                "name": getattr(channel, "title", ""),
                "username": getattr(channel, "username", None),
                "profile_photo": profile_url or f"https://t.me/{channel.username}" if getattr(channel, "username", None) else None
            },
            "metadata": {
                "has_media": bool(msg.media),
                "has_links": has_links,
                "language": "am"  # Defaulting to Amharic as per project scope
            }
        }

    # ── Real-time Listening ───────────────────────────────────────────────
    async def listen_for_new_messages(self, callback) -> None:
        """Listen to incoming new messages from configured channels continuously."""
        chats = []
        for ch_ref in config.CHANNELS:
            entity = await self.resolve_channel(ch_ref)
            if entity:
                chats.append(entity)
                
        if not chats:
            logger.error("No valid channels to listen to!")
            return

        chat_ids = [c.id for c in chats]
        
        # Profile photos map for listener
        profile_urls = {}

        @self.client.on(events.NewMessage(chats=chat_ids))
        async def new_message_handler(event):
            msg = event.message
            channel = await event.get_chat()
            
            # Resolve profile photo if not cached
            if channel.id not in profile_urls:
                try:
                    from media_handler import upload_to_cloudinary
                    photo_bytes = await self.client.download_profile_photo(channel, bytes)
                    if photo_bytes:
                        profile_urls[channel.id] = await upload_to_cloudinary(
                            photo_bytes, 
                            folder="channel_profiles", 
                            public_id=f"channel_{channel.id}"
                        )
                except:
                    pass

            formatted_msg = await self._format_message(msg, channel, profile_urls.get(channel.id))
            if formatted_msg:
                await callback(formatted_msg)

        logger.info(f"Listening for new messages on {len(chats)} channels... (Press Ctrl+C to stop)")
        await self.client.run_until_disconnected()

    # ── Convenience: scrape all configured channels ───────────────────────
    async def scrape_all(self) -> AsyncGenerator[dict, None]:
        """Iterate over every configured channel and yield message dicts."""
        for ch_ref in config.CHANNELS:
            channel = await self.resolve_channel(ch_ref)
            if channel is None:
                continue
            async for msg_dict in self.iter_messages(channel):
                yield msg_dict
