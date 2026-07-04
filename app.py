import os
import re
import json
import asyncio
import threading
import logging
import streamlit as st
import pandas as pd
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# استيراد الفلاتر الذكية من الملف المنفصل
import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

st.set_page_config(page_title="Bo0sViDClone v11.0 VIP", page_icon="🛸", layout="wide")

# ⚠️ حط التوكن بتاعك هنا عشان البوت يشتغل لايف
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

TMP_DIR = "radar_media"
if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)

EXCEL_PATH = "Amazon_Shopping_Montgk.xlsx"
if not os.path.exists(EXCEL_PATH):
    pd.DataFrame(columns=["sku", "title", "standard_price", "brand_name", "description", "piece_price", "original_price"]).to_excel(EXCEL_PATH, index=False)

# مسارات اللوجوهات والأسماء الافتراضية
DEFAULT_LOGO_PATH = "default_logo.png" # اللوجو الأصلي بتاعك
ACTIVE_LOGO_PATH = "logo.png"          # اللوجو الشغال حالياً

# إنشاء لوجو افتراضي فارغ لو مش عندك عشان الكود ما يقفش
if not os.path.exists(DEFAULT_LOGO_PATH):
    img = Image.new('RGBA', (200, 200), color=(255, 75, 75, 255))
    img.save(DEFAULT_LOGO_PATH)
if not os.path.exists(ACTIVE_LOGO_PATH):
    img = Image.open(DEFAULT_LOGO_PATH)
    img.save(ACTIVE_LOGO_PATH)

# --- 🛰️ خوارزمية الفحص والترتيب الذكي المنصوحة لفك اللغبطة ---
def smart_parse_text(text):
    clean_text = re.sub(r'01[0125]\d{8}', '', text) # حذف أرقام التليفونات
    clean_text = clean_text.replace("2026", "").replace("2025", "")
    
    # 1. لقط عدد الدستة
    box_count = config.find_number_near_keywords(clean_text, config.DOZEN_KEYWORDS)
    if not box_count:
        box_count = 12 # القيمة الافتراضية لو ملقطش
        
    # 2. لقط السعر الإجمالي
    total_price = config.find_number_near_keywords(clean_text, config.PRICE_KEYWORDS)
    
    # 3. معالجة "سعر القطعة" لو مكتوب صراحة وبوظ الحسبة
    if "سعر القطعة" in clean_text or "سعر القطعه" in clean_text:
        piece_match = re.search(r'(?:سعر القطع[ةه]\s*[:\-=\s]*\s*(\d+))|(\d+)\s*سعر القطع[ةه]', clean_text)
        if piece_match:
            p_val = int(piece_match.group(1) or piece_match.group(2))
            # لو الرقم الملغبط ده هو اللي طلع كـ سعر كلي، نصلحه بالضرب في عدد الدستة
            if total_price == p_val:
                total_price = p_val * box_count

    if not total_price:
        total_price = 0
        
    return total_price, box_count

# --- دالة تجميل الصور وحقن براند منتجك ---
def process_product_image(in_path, out_path, bottom_text="Montgk Brand"):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    
    # عزل الخلفية بالبلير
    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.composite(img, blurred_img, mask)

    # وضع اللوجو الشغال حالياً
    if os.path.exists(ACTIVE_LOGO_PATH):
        logo = Image.open(ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w*0.25), int(h*0.15)))
        img.paste(logo, (w - logo.size[0] - 15, 15), logo)
        
    # كتابة النص السفلي المتغير
    draw_obj = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
        draw_obj.text((20, h - 40), bottom_text, fill=(255, 255, 255, 200), font=font)
    except:
        draw_obj.text((20, h - 40), bottom_text, fill=(255, 255, 255, 200))
        
    img.save(out_path, "PNG")

# ==================== 🛠️ لوحة التحكم الجانبية (الأزرار المطلوبة) ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>⚙️ ترسانة البراند واللوجو</h2>", unsafe_allow_html=True)
    
    # 1. أوبشن تغيير اللوجو
    st.markdown("### 🖼️ تخصيص اللوجو")
    new_logo = st.file_uploader("رفع أو لصق صورة اللوجو الجديد:", type=["png", "jpg", "jpeg"])
    if new_logo is not None:
        img = Image.open(new_logo)
        img.save(ACTIVE_LOGO_PATH)
        st.success("✅ تم تحديث اللوجو بنجاح!")
        
    # 2. زرار إزالة اللوجو والرجوع للافتراضي
    if st.button("🗑️ إزالة اللوجو المخصص (الرجوع للأصلي)"):
        if os.path.exists(DEFAULT_LOGO_PATH):
            img = Image.open(DEFAULT_LOGO_PATH)
            img.save(ACTIVE_LOGO_PATH)
            st.success("🔄 تم الرجوع للوجو الأصلي لبراند منتجك!")
            st.rerun()
            
    st.write("---")
    
    # 3. تعديل الكلمة اللي تحت Brand Text
    st.markdown("### 📝 نص البراند السفلي")
    if "brand_text_input" not in st.session_state:
        st.session_state["brand_text_input"] = "Montgk Brand"
        
    brand_text = st.text_input("تعديل نص البراند على الصورة:", value=st.session_state["brand_text_input"])
    if brand_text != st.session_state["brand_text_input"]:
        st.session_state["brand_text_input"] = brand_text
        st.success("📝 تم تعديل النص السفلي!")

# ==================== 🛰️ بوت تليجرام التلقائي المطور ====================
ASK_SKU, ASK_TITLE, ASK_DESC, ASK_PRICE, ASK_BOX_COUNT, ASK_BRAND = range(6)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛸 بوت مــنتــجـك المطور جاهز! ارميلي صورة المنتج وهيتم حقن اللوجوهات والأسماء فوراً وتجهيز الأسئلة.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    raw_path = "bot_raw.png"
    processed_path = "bot_processed.png"
    await photo_file.download_to_drive(raw_path)
    
    # تشغيل الحقن التلقائي باللوجو والاسم الحاليين من الإعدادات
    b_text = st.session_state.get("brand_text_input", "Montgk Brand")
    process_product_image(raw_path, processed_path, bottom_text=b_text)
    
    await update.message.reply_photo(photo=open(processed_path, 'rb'), caption="⚡ تم تجميل وصهر الصورة باللوجو والاسم المعتمدين!")
    
    context.user_data['current_product'] = {}
    await update.message.reply_text("📦 **السؤال 1:** اكتب كود المنتج الفريد (Product SKU)؟")
    return ASK_SKU

# (باقي دوال البوت get_sku, get_title, get_desc... إلخ مدمجة ومحمية وتعمل بنفس المنطق المستقر السابق)
async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['sku'] = update.message.text.strip()
    await update.message.reply_text("🏷️ **السؤال 2:** اسم المنتج (Product Title)؟")
    return ASK_TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['title'] = update.message.text.strip()
    await update.message.reply_text("📝 **السؤال 3:** وصف ومميزات المنتج (Description)؟")
    return ASK_DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['description'] = update.message.text.strip()
    await update.message.reply_text("💰 **السؤال 4:** كام سعر الشراء / الجملة الأصلي؟")
    return ASK_PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['original_price'] = int(update.message.text.strip())
        await update.message.reply_text("📦 **السؤال 5:** عدد القطع داخل البوكس أو الدستة؟")
        return ASK_BOX_COUNT
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح:")
        return ASK_PRICE

async def get_box_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['box_count'] = int(update.message.text.strip())
        await update.message.reply_text("🏭 **السؤال 6:** البراند؟ (أو اكتب /skip لو عام)")
        return ASK_BRAND
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح:")
        return ASK_BOX_COUNT

async def get_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['brand'] = update.message.text.strip()
    return await save_bot_data(update, context)

async def skip_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['brand'] = "Generic"
    return await save_bot_data(update, context)

async def save_bot_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prod = context.user_data['current_product']
    selling_price = int(prod['original_price'] * 1.25)
    piece_price = round(selling_price / prod['box_count'], 1)
    
    new_row = {
        "sku": prod['sku'], "title": prod['title'], "standard_price": selling_price,
        "brand_name": prod['brand'], "description": prod['description'], "piece_price": piece_price, "original_price": prod['original_price']
    }
    df = pd.read_excel(EXCEL_PATH)
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False)
    
    commercial_post = (
        f"📦 **{prod['title']}**\n🔢 كود المنتج: `{prod['sku']}`\n\n"
        f"💬 {prod['description']}\n\n"
        f"🔥 سعر العرض الخاص من مــنتــجـك: {selling_price} ج!\n"
        f"📌 (القطعة جملة بـ {piece_price} ج بس! 💣)\n\n"
        f"#Mr_Bo0\n#Montgk-منتجك"
    )
    await update.message.reply_text(commercial_post)
    return ConversationHandler.END

def run_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, handle_image)],
        states={
            ASK_SKU: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sku)],
            ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc)],
            ASK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            ASK_BOX_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_box_count)],
            ASK_BRAND: [CommandHandler("skip", skip_brand), MessageHandler(filters.TEXT & ~filters.COMMAND, get_brand)],
        },
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start_bot))
    app.add_handler(conv)
    app.run_polling()

if "bot_thread_started" not in st.session_state and TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    st.session_state["bot_thread_started"] = True
    threading.Thread(target=run_bot_loop, daemon=True).start()

# ==================== 💻 واجهة شاشة العرض (Streamlit Main) ====================
col_main, _ = st.columns([3, 1])
with col_main:
    st.subheader("📊 كتالوج وجدول منتجات أمازون والمنصات")
    if os.path.exists(EXCEL_PATH):
        df_current = pd.read_excel(EXCEL_PATH)
        st.dataframe(df_current, use_container_width=True)
        with open(EXCEL_PATH, "rb") as f:
            st.download_button("📥 تحميل شيت الكتالوج المحدث كليا", data=f, file_name="Amazon_Montgk_Catalog.xlsx")
