"""
One-Time Migration Script
Flattens all existing nested scraper documents in MongoDB to the 
new unified flat schema matching the backend Mongoose model.

Usage:
    python migrate_flatten_schema.py

This is safe to run multiple times — it skips documents that are 
already in the flat format.
"""

import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("migration")


def run_migration():
    try:
        from pymongo import MongoClient
        import certifi
    except ImportError:
        logger.error("pymongo or certifi not installed. Run: pip install pymongo certifi")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL")
    db_name = os.getenv("MONGODB_DB_NAME", "telegram_news")
    collection_name = os.getenv("MONGODB_COLLECTION", "news")

    if not db_url:
        logger.error("DATABASE_URL not set in .env")
        sys.exit(1)

    client = MongoClient(db_url, tlsCAFile=certifi.where())
    db = client[db_name]
    collection = db[collection_name]

    total = collection.count_documents({})
    logger.info(f"Found {total} documents in {db_name}.{collection_name}")

    # Find documents that still have the old nested format
    # (they have a nested 'channel' object or nested 'content' object)
    old_format_query = {
        "$or": [
            {"channel": {"$type": "object"}},
            {"content": {"$type": "object"}},
            {"engagement": {"$exists": True}},
            {"media": {"$type": "object"}},
            {"metadata": {"$type": "object"}},
            {"status": {"$type": "object"}},
        ]
    }

    old_docs = collection.count_documents(old_format_query)
    logger.info(f"Found {old_docs} documents with old nested format to migrate")

    if old_docs == 0:
        logger.info("✅ No documents need migration. All good!")
        client.close()
        return

    migrated = 0
    errors = 0
    cursor = collection.find(old_format_query, no_cursor_timeout=True)

    try:
        for doc in cursor:
            try:
                update = {}
                unset = {}

                # ── Flatten channel ──
                channel = doc.get("channel")
                if isinstance(channel, dict):
                    if not doc.get("channelName"):
                        update["channelName"] = channel.get("name", "")
                    if not doc.get("channelUsername"):
                        update["channelUsername"] = channel.get("username", "")
                    if not doc.get("channelProfilePic"):
                        update["channelProfilePic"] = channel.get(
                            "profile_picture",
                            channel.get("profile_photo", channel.get("channel_profile_picture"))
                        )
                    if not doc.get("channel_id"):
                        update["channel_id"] = channel.get("id")
                    unset["channel"] = ""

                # ── Flatten content ──
                content = doc.get("content")
                if isinstance(content, dict):
                    clean_text = content.get("clean_text", content.get("raw_text", ""))
                    raw_text = content.get("raw_text", "")
                    update["content"] = clean_text
                    if not doc.get("rawText"):
                        update["rawText"] = raw_text
                    # Don't unset 'content' since we're overwriting it as a string

                # ── Flatten engagement ──
                engagement = doc.get("engagement")
                if isinstance(engagement, dict):
                    if doc.get("views") is None or doc.get("views") == 0:
                        update["views"] = engagement.get("views") or 0
                    if not doc.get("likesCount"):
                        update["likesCount"] = engagement.get("like_count") or 0
                    if not doc.get("commentsCount"):
                        update["commentsCount"] = engagement.get("comment_count") or 0
                    unset["engagement"] = ""

                # ── Flatten media ──
                media = doc.get("media")
                if isinstance(media, dict):
                    if not doc.get("mediaUrl"):
                        update["mediaUrl"] = media.get("image_url")
                    if not doc.get("videoUrl"):
                        update["videoUrl"] = media.get("video_url")
                    unset["media"] = ""

                # ── Flatten metadata ──
                metadata = doc.get("metadata")
                if isinstance(metadata, dict):
                    if not doc.get("language"):
                        update["language"] = metadata.get("language", "am")
                    if doc.get("hasMedia") is None:
                        update["hasMedia"] = metadata.get("has_media", False)
                    if doc.get("hasLinks") is None:
                        update["hasLinks"] = metadata.get("has_links", False)
                    if not doc.get("mediaType"):
                        update["mediaType"] = metadata.get("media_type")
                    # Migrate old news_text if content is still missing
                    if not update.get("content") and not isinstance(doc.get("content"), str):
                        news_text = metadata.get("news_text")
                        if news_text:
                            update["content"] = news_text
                    unset["metadata"] = ""

                # ── Flatten status ──
                status = doc.get("status")
                if isinstance(status, dict):
                    update["status"] = "published"
                    # Remove the nested status object (it had is_cleaned, is_labeled, etc.)

                # ── Fix telegramId ──
                if not doc.get("telegramId") and doc.get("message_id"):
                    channel_id = doc.get("channel_id") or (channel.get("id") if isinstance(channel, dict) else "")
                    update["telegramId"] = f"{channel_id}_{doc['message_id']}"

                # ── Fix source field ──
                if not doc.get("source"):
                    update["source"] = "telegram"

                # ── Fix publishedAt ──
                if not doc.get("publishedAt") and doc.get("date"):
                    update["publishedAt"] = doc["date"]

                # ── Build sourceUrl ──
                if not doc.get("sourceUrl"):
                    username = update.get("channelUsername") or doc.get("channelUsername")
                    msg_id = doc.get("message_id")
                    if username and msg_id:
                        update["sourceUrl"] = f"https://t.me/{username}/{msg_id}"

                # ── Remove legacy fields ──
                for field in ["text", "news_text", "clean_text", "channel_id_old",
                              "like_count", "comment_count", "repost", "likes",
                              "source_url", "label", "summary"]:
                    if field in doc and field not in ["label", "summary"]:
                        # Keep label and summary if they have values
                        if field in ["label", "summary"] and doc.get(field):
                            continue
                        # Rename 'text' → we already have rawText
                        if field == "text" and not update.get("rawText") and not doc.get("rawText"):
                            update["rawText"] = doc[field]
                        unset[field] = ""

                # Apply the update
                ops = {}
                if update:
                    ops["$set"] = update
                if unset:
                    ops["$unset"] = unset

                if ops:
                    collection.update_one({"_id": doc["_id"]}, ops)
                    migrated += 1

                if migrated % 100 == 0 and migrated > 0:
                    logger.info(f"  … migrated {migrated}/{old_docs} documents")

            except Exception as e:
                errors += 1
                logger.warning(f"Error migrating doc {doc.get('_id')}: {e}")

    finally:
        cursor.close()

    logger.info("─" * 60)
    logger.info(f"✅ Migration complete: {migrated} migrated, {errors} errors")
    logger.info("─" * 60)

    client.close()


if __name__ == "__main__":
    run_migration()
