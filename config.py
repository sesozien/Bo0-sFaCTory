import os
import json

PAGE_TITLE = "Bo0'sViDClone V12.0 Ultra Smart"
PAGE_ICON = "🛰️"
BRAND_NAME_AR = "مصنع تجميل وإدارة المحتوى الذكي"
DEVELOPER_SIGNATURE = "Developed with ⚡ by Mr:- Bo0"

TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

DEFAULT_LOGO_PATH = "default_logo.png"
ACTIVE_LOGO_PATH = "active_logo.png"
CUSTOM_AUDIO_TRACK = "custom_track.mp3"
CHANNELS_FILE = "channels.json"
KEYWORDS_FILE = "price_keywords.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ضع_التوكن_الافتراضي_هنا")

DEFAULT_PRICE_INC_RATE = 20
DEFAULT_BOX_ITEMS_COUNT = 12

def get_price_keywords():
    default_keywords = ["سعر", "السعر", "جنية", "جنيه", "جـ", "egp", "EGP", "LE", "للباكت", "للدرزن", "بـ", "للقطعة"]
    if os.path.exists(KEYWORDS_FILE):
        try:
            with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and loaded:
                    return loaded
        except:
            pass
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_keywords, f, ensure_ascii=False, indent=4)
    return default_keywords

def load_and_sync_channels():
    default_channels = ["montgk", "egypt_trends_store", "B00_Store"]
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and loaded:
                    return loaded
        except:
            pass
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_channels, f, ensure_ascii=False, indent=4)
    return default_channels
