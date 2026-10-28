import json
import os
import tempfile

PAGE_TITLE = "Bo0'sViDClone V13.0 Ultimate"
PAGE_ICON = "🛰️"
APP_VERSION = "radar-cleanup-1"
BRAND_NAME_AR = "مصنع تجميل وإدارة المحتوى الذكي"
DEVELOPER_SIGNATURE = "Developed with ⚡ by Mr:- Bo0"

TMP_DIR = "tmp_files"
os.makedirs(TMP_DIR, exist_ok=True)

PROJECT_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
DEFAULT_LOGO_PATH = "default_logo.png"
ACTIVE_LOGO_PATH = "active_logo.png"
CUSTOM_AUDIO_TRACK = "custom_track.mp3"
CHANNELS_FILE = "channels.json"
KEYWORDS_FILE = "price_keywords.json"
SETTINGS_FILE = "settings.json"
CATALOG_FILE = "catalog.json"
CATEGORIES_FILE = "catalog_categories.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ضع_التوكن_الافتراضي_هنا")

DEFAULT_PRICE_INC_RATE = 20
DEFAULT_BOX_ITEMS_COUNT = 12

# فقط القيم البسيطة التي يمكن تحويلها بأمان إلى JSON تُحفظ بين جلسات Streamlit.
PERSISTED_SETTING_KEYS = {
    "c_preset", "platform_dim", "font_sel", "l_pos", "l_ox", "l_oy", "l_op",
    "logo_fit_auto", "rem_bg_chk", "logo_mode", "logo_w", "logo_h", "dynamic_brand_text",
    "b_pos", "b_ox", "b_oy", "b_sc", "b_cl", "e_text", "e_pos", "e_ox",
    "e_oy", "e_sc", "e_cl", "blur_bg", "blur_val", "enhance_opt", "sharp_val",
    "q_val", "enable_crop", "c_l", "c_t", "c_r", "c_b", "audio_mode",
    "vid_option_main", "enable_trim_key", "t_start", "t_end", "sp_mode", "sp_factor",
    "t_dur_sec", "show_orig_tab2", "p_rate", "b_items", "fb_url", "max_p", "d_filt",
    "r_mode", "sel_ch", "trend_cat", "radar_profit", "radar_max_messages", "radar_max_price",
    "radar_source_rule", "radar_rounding", "radar_review_required", "radar_auto_publish", "radar_publish_channel",
}


def get_price_keywords():
    default_keywords = ["سعر", "السعر", "جنية", "جنيه", "جـ", "egp", "EGP", "LE", "للباكت", "للدرزن", "بـ", "للقطعة"]
    if os.path.exists(KEYWORDS_FILE):
        try:
            with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and loaded:
                    return loaded
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_keywords, f, ensure_ascii=False, indent=4)
    return default_keywords


def load_settings():
    """Load saved widget values; a broken file should never stop the app."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return {key: loaded[key] for key in PERSISTED_SETTING_KEYS if key in loaded} if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def save_settings(values):
    """Atomically save the current Streamlit widget state."""
    payload = {key: values[key] for key in PERSISTED_SETTING_KEYS if key in values}
    directory = os.path.dirname(os.path.abspath(SETTINGS_FILE)) or "."
    try:
        fd, temp_path = tempfile.mkstemp(prefix="settings_", suffix=".json", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, SETTINGS_FILE)
    except OSError:
        try:
            if "temp_path" in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def load_and_sync_channels():
    default_channels = ["montgk", "egypt_trends_store", "B00_Store"]
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list) and loaded:
                    return loaded
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(default_channels, f, ensure_ascii=False, indent=4)
    return default_channels


def load_catalog():
    if not os.path.exists(CATALOG_FILE):
        return []
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []

def save_catalog(rows):
    directory = os.path.dirname(os.path.abspath(CATALOG_FILE)) or "."
    try:
        fd, temp_path = tempfile.mkstemp(prefix="catalog_", suffix=".json", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, CATALOG_FILE)
        return True
    except OSError:
        return False


def load_categories():
    if not os.path.exists(CATEGORIES_FILE):
        return []
    try:
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []

def save_categories(categories):
    try:
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(list(dict.fromkeys(categories)), f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
