# 📰 Telegram News Scraper — ML Training Data Pipeline

Scrapes news from Telegram channels, cleans the text, and exports structured data
ready for training NLP / text-classification models.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get your Telegram API credentials
1. Go to **https://my.telegram.org**
2. Log in → "API development tools" → Create an app
3. Copy your **API ID** and **API Hash**

### 3. Configure
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
```

Edit **`.env`**:
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE_NUMBER=+251912345678
```

Then add your target channels in **`config.py`**:
```python
CHANNELS = [
    "example_news_channel",
    "another_channel",
]
```

### 4. Run the pipeline
```bash
# Scrape all channels defined in config.py
python pipeline.py

# Or scrape a specific channel with a custom limit
python pipeline.py --channel example_channel --limit 2000
```

On the first run you'll be prompted to enter the login code sent to your Telegram.

---

## Output

Data is saved in `data/` in both **JSONL** and **CSV** by default:

| File | Format | Best For |
|------|--------|----------|
| `telegram_news_*.jsonl` | JSON Lines | HuggingFace `datasets`, streaming |
| `telegram_news_*.csv` | CSV | pandas, spreadsheets |

### Record schema
```json
{
  "message_id": 12345,
  "channel_id": -1001234567890,
  "channel_title": "Example News",
  "date": "2026-03-11T10:30:00+00:00",
  "raw_text": "🔴 BREAKING: ... #news https://t.me/...",
  "news_text": "BREAKING: cleaned news text here",
  "views": 4200,
  "media_url": "https://cloudinary.com/...",
  "video_url": "https://cloudinary.com/..."
}
```

---

## Project Structure

```
Scraping/
├── .env.example          # Template for API credentials
├── .env                  # Your actual credentials (git-ignored)
├── .gitignore            # Keeps secrets & output out of version control
├── config.py             # Channels, settings, loads .env
├── telegram_scraper.py   # Telethon-based async scraper
├── telegram_cleaner.py   # Text cleaning (URLs, emojis, hashtags, …)
├── data_exporter.py      # JSONL / CSV / JSON writers
├── pipeline.py           # Main entry point
├── requirements.txt      # Python dependencies
└── data/                 # Output directory (auto-created)
    ├── telegram_news_*.jsonl
    └── telegram_news_*.csv
```

---

## Cleaning Rules

The cleaner removes:
- ✂️ **URLs** — `https://...`, `t.me/...`
- ✂️ **Emojis** — all Unicode emoji ranges
- ✂️ **Hashtags** — `#BreakingNews`
- ✂️ **Mentions** — `@channel_name`
- ✂️ **CTA lines** — "Join", "Subscribe", "Share", "ተቀላቀሉን"
- ✂️ **Symbols** — arrows, dingbats, misc Unicode

### Media Handling
- 📸 **Images** — Automatic upload to Cloudinary
- 🎥 **Videos** — Support for video content (uploaded as video resource)
- 📄 **Documents** — Other media types are also processed via Cloudinary's auto-detection

It preserves:
- ✅ Latin characters
- ✅ **Ethiopic / Amharic / Ge'ez** characters
- ✅ Digits and basic punctuation

---

## Using the Data for Training

### Load with HuggingFace Datasets
```python
from datasets import load_dataset
ds = load_dataset("json", data_files="data/telegram_news_*.jsonl")
```

### Load with pandas
```python
import pandas as pd
df = pd.read_csv("data/telegram_news_20260311_143000.csv")
print(df["news_text"].head())
```
