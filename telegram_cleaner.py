"""
Telegram Message Cleaner
Extracts clean news text from Telegram messages by removing:
  - URLs
  - Emojis
  - Hashtags
  - Mentions (@username)
  - Unnecessary symbols
  - "Join/Subscribe" call-to-action lines
Returns the result as JSON: { "news_text": "..." }
"""

import re
import json
import sys


# ── Pre-compiled patterns ─────────────────────────────────────────────────────
_URL_RE = re.compile(r'https?://\S+|ftp://\S+|www\.\S+|t\.me/\S+', re.I)
_HASHTAG_RE = re.compile(r'#\w+')
_MENTION_RE = re.compile(r'@\w+')
_CTA_RE = re.compile(
    r'^.*?(join|subscribe|follow|share|forward|ተቀላቀሉን|ሼር).*?$',
    re.I | re.MULTILINE,
)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000203C-\U00003299"
    "]+",
    flags=re.UNICODE,
)
# Keep: word chars, whitespace, basic punctuation, Ethiopic scripts
_SYMBOL_RE = re.compile(
    r"[^\w\s.,;:!?'\"()\-/\u1200-\u137F\u1380-\u139F\u2D80-\u2DDF\u1400-\u167F]"
)
_MULTI_SPACE_RE = re.compile(r'[ \t]+')
_MULTI_NEWLINE_RE = re.compile(r'\n\s*\n+')


def clean_telegram_message(telegram_message: str) -> dict:
    """
    Clean a Telegram message by removing URLs, emojis, hashtags,
    mentions, symbols, and CTA lines.  Returns a dict with cleaned text.
    """
    text = telegram_message

    # 1. URLs
    text = _URL_RE.sub('', text)

    # 2. Hashtags
    text = _HASHTAG_RE.sub('', text)

    # 3. Mentions
    text = _MENTION_RE.sub('', text)

    # 4. CTA / promo lines
    text = _CTA_RE.sub('', text)

    # 5. Emojis
    text = _EMOJI_RE.sub('', text)

    # 6. Remaining symbols
    text = _SYMBOL_RE.sub('', text)

    # 7. Normalize whitespace
    text = _MULTI_SPACE_RE.sub(' ', text)
    text = _MULTI_NEWLINE_RE.sub('\n', text)
    text = text.strip()

    return {"news_text": text}


def clean_batch(messages: list[str]) -> list[dict]:
    """Clean a list of raw messages and return list of result dicts."""
    return [clean_telegram_message(m) for m in messages]


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python telegram_cleaner.py "<telegram_message>"')
        sys.exit(1)

    raw_message = sys.argv[1]
    result = clean_telegram_message(raw_message)
    print(json.dumps(result, ensure_ascii=False, indent=2))
