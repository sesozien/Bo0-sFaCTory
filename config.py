import os
import json

# 🛸 إعدادات المنصة الأساسية وبراند مــنتــجـك
PAGE_TITLE = "Bo0sViDClone v9.5 Ultimate"
PAGE_ICON = "🛸"
BRAND_NAME_AR = "🎬 MOntgk - مــنتــجـك"
DEVELOPER_SIGNATURE = "🛸 تم التطوير والأداء بكل فخامة بواسطة: MR Bo0 🛸"

# 📁 مسارات المجلدات والملفات الميديا
TMP_DIR = "radar_media"
CHANNELS_FILE = "registered_channels.json"
EXCEL_PATH = "Amazon_Shopping_Montgk.xlsx"
ACTIVE_LOGO_PATH = "logo.png"
DEFAULT_LOGO_PATH = "default_logo.png"
CUSTOM_AUDIO_TRACK = "my_luxury_brand_track.wav"

# 🛰️ القنوات الافتراضية المفضلة اللي عايز المصنع يلقطها عل طول من أول تشغيلة
# (تقدر تعدل أو تضيف يوزرات القنوات هنا براحتك في اللستة دي)
DEFAULT_RADAR_CHANNELS = [
    "Baghdadi011",
    "Gomla_El_Azhar",   # مثال لقناة تانية ضفتها لك
    "Star_Store_Gomla"  # مثال لقناة تالتة
]

# ⚙️ دالة ذكية لإدارة وحفظ القنوات عشان تسمّع في ملف الـ JSON وماتتمسحش أبداً
def load_and_sync_channels():
    if not os.path.exists(CHANNELS_FILE):
        # لو الملف مش موجود.. بننشئه باليوزرات الافتراضية اللي فوق
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_RADAR_CHANNELS, f, ensure_ascii=False, indent=4)
        return DEFAULT_RADAR_CHANNELS
    else:
        # لو الملف موجود.. بنقرا منه القنوات المحفوظة بما فيها القنوات الجديدة اللي ضفتها من الواجهة
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                saved_channels = json.load(f)
                # للتأكد من إن القنوات الافتراضية دايماً موجودة حتى لو الملف اتمسح منه حاجة بالغلط
                for ch in DEFAULT_RADAR_CHANNELS:
                    if ch not in saved_channels:
                        saved_channels.append(ch)
                return saved_channels
        except:
            return DEFAULT_RADAR_CHANNELS

# 🛰️ دمج الكلمات المفتاحية الأسطورية (بتاعتك + بتاعتي) لعدم تفويت أي بوست
DOZEN_KEYWORDS = [
    "عدد الدست", "عدد الدسته", "الكرتونه", "الكرترونه", 
    "عدد الكرتونه", "عدد الكرترونه", "عدد القطع", "عدد العلبه", "العلبه فيها",
    "دستة", "دسته", "علبة", "علبه", "كرتونة", "كرtونه", "بوكس", "مجموعة", "مجموعه", "عدد"
]

# مرتبة من الأطول للأقصر عشان الـ Regex يلقط الجمل المركبة الأول
PRICE_KEYWORDS = [
    "السعر للدسته", "سعر الدسته", "سعر العلبه", "سعر الاستاند", "بعد العرض", 
    "البوكس بـ", "الدسته بـ", "سعر البوكس", "تكلفتها", "تكلفتة", "جنيه", 
    "جنية", "السعر", "جملة", "جمله", "شراء", "تكلفة", "واقف", "واقفة", "بسعر", "سعر", "ج"
]

# 🔒 توكنات الحسابات وبوت التليجرام
TELEGRAM_BOT_TOKEN = "8685178390:AAEgzrKz2yHW2oeflsZyZMeSN1Nw0da3vvI"

# 🛡️ الإعدادات الافتراضية
DEFAULT_PRICE_INC_RATE = 25
DEFAULT_BOX_ITEMS_COUNT = 12

if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)
