"""
Data Exporter
Saves cleaned Telegram messages to the database.
"""

import logging
import config

logger = logging.getLogger(__name__)

# Fields written to the database
FIELDS = [
    "message_id",
    "channel_id",
    "channel_name",
    "channel_profile_picture",
    "channel_username",
    "date",
    "raw_text",
    "news_text",
    "views",
    "forwards",
    "repost",
    "likes",
    "like_count",
    "comment_count",
    "media_url",
]


# ── MongoDB ───────────────────────────────────────────────────────────────────
class MongoDBExporter:
    """Exports records to a MongoDB collection."""

    def __init__(self):
        if not config.DATABASE_URL:
            logger.error("DATABASE_URL not set. MongoDB export will fail.")
            self._client = None
            return

        try:
            from pymongo import MongoClient
            import certifi
            self._client = MongoClient(config.DATABASE_URL, tlsCAFile=certifi.where())
            self._db = self._client[config.MONGODB_DB_NAME]
            self._collection = self._db[config.MONGODB_COLLECTION]
            logger.info(f"MongoDB output → {config.MONGODB_DB_NAME}.{config.MONGODB_COLLECTION}")
        except ImportError:
            logger.error("Module 'pymongo' or 'certifi' not found. Please run 'pip install pymongo certifi'")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._client = None

    def write(self, record: dict) -> None:
        if self._client:
            # We use update_one with upsert=True to avoid duplicates if re-running
            query = {"message_id": record["message_id"], "channel.id": record["channel"]["id"]}
            self._collection.update_one(query, {"$set": record}, upsert=True)

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")


# ── Factory ───────────────────────────────────────────────────────────────────
EXPORTERS = {
    "mongodb": MongoDBExporter,
}


def create_exporters() -> list:
    """Instantiate exporters for every format listed in config."""
    return [EXPORTERS[fmt]() for fmt in config.OUTPUT_FORMATS if fmt in EXPORTERS]
