"""
Data Exporter
Saves cleaned Telegram messages to disk in ML-ready formats:
  - JSONL  (one JSON object per line — ideal for streaming / HuggingFace datasets)
  - CSV    (easy to load with pandas)
  - JSON   (single JSON array)
"""

import csv
import json
import os
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)

# Fields written to every output format
FIELDS = [
    "message_id",
    "channel_id",
    "channel_title",
    "date",
    "raw_text",
    "news_text",
    "views",
    "forwards",
]


def _ensure_dir() -> str:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    return config.OUTPUT_DIR


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── JSONL ─────────────────────────────────────────────────────────────────────
class JSONLExporter:
    """Append-friendly JSONL writer with periodic flushing."""

    def __init__(self, filename: str | None = None):
        out_dir = _ensure_dir()
        self.path = os.path.join(
            out_dir, filename or f"telegram_news_{_timestamp()}.jsonl"
        )
        self._file = open(self.path, "a", encoding="utf-8")
        self._count = 0
        logger.info(f"JSONL output → {self.path}")

    def write(self, record: dict) -> None:
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._count += 1
        if self._count % 50 == 0:
            self._file.flush()

    def close(self) -> None:
        self._file.flush()
        self._file.close()
        logger.info(f"JSONL file saved: {self.path}")


# ── CSV ───────────────────────────────────────────────────────────────────────
class CSVExporter:
    """CSV writer with header auto-detection."""

    def __init__(self, filename: str | None = None):
        out_dir = _ensure_dir()
        self.path = os.path.join(
            out_dir, filename or f"telegram_news_{_timestamp()}.csv"
        )
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDS)
        self._writer.writeheader()
        logger.info(f"CSV output → {self.path}")

    def write(self, record: dict) -> None:
        row = {k: record.get(k, "") for k in FIELDS}
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()
        logger.info(f"CSV file saved: {self.path}")


# ── JSON (array) ──────────────────────────────────────────────────────────────
class JSONExporter:
    """Collects all records in memory, writes a single JSON array on close."""

    def __init__(self, filename: str | None = None):
        out_dir = _ensure_dir()
        self.path = os.path.join(
            out_dir, filename or f"telegram_news_{_timestamp()}.json"
        )
        self._records: list[dict] = []
        logger.info(f"JSON output → {self.path}")

    def write(self, record: dict) -> None:
        self._records.append(record)

    def close(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON file saved: {self.path} ({len(self._records)} records)")


# ── MongoDB ───────────────────────────────────────────────────────────────────
class MongoDBExporter:
    """Exports records to a MongoDB collection."""

    def __init__(self):
        if not config.DATABASE_URL:
            logger.error("DATABASE_URL not set. MongoDB export will fail.")
            self._client = None
            return

        from pymongo import MongoClient

        self._client = MongoClient(config.DATABASE_URL)
        self._db = self._client[config.MONGODB_DB_NAME]
        self._collection = self._db[config.MONGODB_COLLECTION]
        logger.info(f"MongoDB output → {config.MONGODB_DB_NAME}.{config.MONGODB_COLLECTION}")

    def write(self, record: dict) -> None:
        if self._client:
            # We use update_one with upsert=True to avoid duplicates if re-running
            query = {"message_id": record["message_id"], "channel_id": record["channel_id"]}
            self._collection.update_one(query, {"$set": record}, upsert=True)

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")


# ── Factory ───────────────────────────────────────────────────────────────────
EXPORTERS = {
    "jsonl": JSONLExporter,
    "csv": CSVExporter,
    "json": JSONExporter,
    "mongodb": MongoDBExporter,
}


def create_exporters() -> list:
    """Instantiate exporters for every format listed in config."""
    return [EXPORTERS[fmt]() for fmt in config.OUTPUT_FORMATS if fmt in EXPORTERS]
