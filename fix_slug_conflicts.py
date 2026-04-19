"""
Fix Slug Conflicts Script
Unsets any 'null' values for unique-indexed fields (slug, telegramId, etc.)
to allow sparse indexes to work correctly.
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
logger = logging.getLogger("fix-slugs")


def run_fix():
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

    # Fields that should be sparse (no nulls allowed if unique)
    unique_fields = ["slug", "telegramId", "title"]

    for field in unique_fields:
        logger.info(f"Unsetting 'null' values for field: {field}")
        result = collection.update_many(
            {field: None},
            {"$unset": {field: ""}}
        )
        logger.info(f"  -> Modified {result.modified_count} documents.")

    logger.info("Done! The sparse indexes should now work correctly without conflicts.")
    client.close()


if __name__ == "__main__":
    run_fix()
