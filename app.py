import os
import re
import json
import asyncio
import threading
import logging
import streamlit as st
import pandas as pd
from PIL import Image, ImageFilter, ImageDraw, ImageFont

# مكتبات التنسيق الفخم لشيت الإكسيل المتغير
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ModuleNotFoundError:
    HAS_TELEGRAM = False

import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

st.set_page_config(page_title="Bo0sViDClone v12.5 VIP", page_icon="🛸", layout="wide")

# 🔒 التوكن النشط والمحفوظ بشكل دائم
TOKEN = "8685178390:AAEgzrKz2yHW2oeflsZyZMeSN1Nw0da3vvI" 

EXCEL_PATH = "Amazon_Shopping_Montgk.xlsx"
ACTIVE_LOGO_PATH = "logo.png"
DEFAULT_LOGO_PATH = "default_logo.png"

# التأكد من وجود ملفات اللوجوهات الافتراضية
if not os.path.exists(DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(DEFAULT_LOGO_PATH)
if not os.path.exists(ACTIVE_LOGO_PATH):
    Image.open(DEFAULT_LOGO_PATH).save(ACTIVE_LOGO_PATH)

# دالة التنسيق الملون الفخم المدمجة في محرك الحفظ للبوت
def save_styled_excel(file_path, new_row):
    # تحميل أو إنشاء جدول البيانات بشكل منظم
    arabic_headers = ["كود المنتج (SKU)", "اسم وعنوان المنتج", "سعر البيع (جنيه)", "اسم البراند", "الوصف والمميزات", "سعر القطعة جملة", "سعر الشراء الأصلي"]
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "كتالوج المنتجات"
    ws.views.sheetView[0].showGridLines = True
    ws.sheet_view.rightToLeft = True # قلب اتجاه الشيت ليناسب اللغة العربية الفخمة

    # باليتة الألوان الهادئة الاحترافية (Pastel / Muted)
    header_fill = PatternFill(start_color="2A4D69", end_color="2A4D69", fill_type="solid") # كحلي هادئ
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F5F7FA", end_color="F5F7FA", fill_type="solid") # رمادي فاتح مريح جداً
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    data_font = Font(name="Arial", size=10, color="000000")
    thin_border = Border(left=Side(style='thin', color='E0E0E0'), right=Side(style='thin', color='E0E0E0'),
                         top=Side(style='thin', color='E0E0E0'), bottom=Side(style='thin', color='E0E0E0'))

    # 1. كتابة الهيدر
    for col_num, header in enumerate(arabic_headers, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # 2. جلب البيانات القديمة بأمان بدون صف التوقيع المتغير
    rows_to_write = []
    if os.path.exists(file_path):
        try:
            # قراءة الشيت القديم كـ DataFrame مؤقت
            old_df = pd.read_excel(file_path)
            for _, r in old_df.iterrows():
                # تصفية أي سطور فارغة أو سطور تحتوي على نص التوقيع فقط
                if pd.notna(r.iloc[0]) and not str(r.iloc[0]).startswith("🛸") and not str(r.iloc[0]).startswith("كود"):
                    rows_to_write.append(list(r[:7]))
        except:
            pass

    # إضافة سطر المنتج الجديد القادم من البوت
    rows_to_write.append([
        new_row["sku"], new_row["title"], new_row["standard_price"],
        new_row["brand_name"], new_row["description"], new_row["piece_price"], new_row["original_price"]
    ])

    # 3. كتابة وتلوين صفوف البيانات
    for row_idx, data in enumerate(rows_to_write, 3):
        current_fill = zebra_fill if row_idx % 2 == 0 else white_fill
        for col_idx, val in enumerate(data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = val
            cell.font = data_font
            cell.fill = current_fill
            cell.border = thin_border
            
            # محاذاة وتنسيق الأرقام
            if isinstance(val, (int, float)):
                cell.number_format = '#,##0.0' if isinstance(val, float) else '#,##0'
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right" if col_idx in [2, 5] else "center", vertical="center")

    # 4. طباعة وتثبيت إمضاء MR Bo0 الفخم في نهاية ملف المنتجات
    sig_row = len(rows_to_write) + 5
    ws.merge_cells(start_row=sig_row, start_column=1, end_row=sig_row, end_column=7)
    sig_cell = ws.cell(row=sig_row, column=1)
    sig_cell.value = "🛸 تم الإنشاء والترتيب بكل فخامة بواسطة: MR Bo0 🛸"
    sig_cell.font = Font(name="Arial", size=12, bold=True, italic=True, color="2A4D69")
    sig_cell.alignment = Alignment(horizontal="center", vertical="center")

    # 5. ضبط الارتفاع وعرض الأعمدة تلقائياً بناءً على حجم النصوص
    ws.row_dimensions[2].height = 28
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 16)

    wb.save(file_path)

# التأكد من تهيئة الملف بالتنسيق الجديد عند أول تشغيل
if not os.path.exists(EXCEL_PATH):
    save_styled_excel(EXCEL_PATH, {"sku":"-", "title":"-", "standard_price":0, "brand_name":"-", "description":"-", "piece_price":0.0, "original_price":0})

# --- 🎯 محرك الترتيب الذكي اللغوي المطور ---
def advanced_smart_parse(text):
    clean_text = re.sub(r'01[0125]\d{8}', '', text)
    clean_text = clean_text.replace("2026", "").replace("2025", "")
    
    box_count = None
    for kw in config.DOZEN_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            box_count = int(match.group(1) or match.group(2))
            break
    if not box_count or box_count == 0:
        box_count = 12

    total_price = None
    for kw in config.PRICE_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            total_price = int(match.group(1) or match.group(2))
            break

    if "سعر القطعة" in clean_text or "سعر القطعه" in clean_text:
        p_match = re.search(r'(?:سعر القطع[ةه]\s*[:\-=\s]*\s*(\d+))|(\d+)\s*سعر القطع[ةه]', clean_text)
        if p_match:
            piece_val = int(p_match.group(1) or p_match.group(2))
            if total_price == piece_val or not total_price:
                total_price = piece_val * box_count

    if not total_price:
        total_price = 0

    return total_price, box_count

def process_product_image(in_path, out_path, bottom_text="Montgk Brand"):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    
    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.composite(img, blurred_img, mask)

    if os.path.exists(ACTIVE_LOGO_PATH):
        logo = Image.open(ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w*0.25), int(h*0.15)))
        img.paste(logo, (w - logo.size[0] - 15, 15), logo)
        
    draw_obj = ImageDraw.Draw(img)
    try:
        draw_obj.text((20, h - 40), bottom_text, fill=(255, 255, 255, 200))
    except: pass
    img.save(out_path, "PNG")

# ==================== 🛠️ لوحة التحكم الجانبية ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛸 تحكم مــنتــجـك VIP</h2>", unsafe_allow_html=True)
    st.markdown("### 🖼️ لوحة تغيير اللوجو")
    new_logo = st.file_uploader("ارفع أو الصق لوجو جديد هنا:", type=["png", "jpg", "jpeg"])
    if new_logo is not None:
        Image.open(new_logo).save(ACTIVE_LOGO_PATH)
        st.success("✅ تم تحديث اللوجو بنجاح في السيرفر!")
        
    if st.button("🔄 إزالة اللوجو المخصص"):
        Image.open(DEFAULT_LOGO_PATH).save(ACTIVE_LOGO_PATH)
        st.success("🔄 تم استعادة اللوجو الافتراضي!")
        st.rerun()
        
    st.write("---")
    st.markdown("### 📝 نص البراند السفلي")
    if "brand_text_input" not in st.session_state:
        st.session_state["brand_text_input"] = "Montgk Brand"
    b_text = st.text_input("تعديل النص المطبوع على الصورة:", value=st.session_state["brand_text_input"])
    if b_text != st.session_state["brand_text_input"]:
        st.session_state["brand_text_input"] = b_text
        st.success("📝 تم تعديل الاسم بنجاح!")

# ==================== 🛰️ محرك البوت الذكي التلقائي (التليجرام) ====================
ASK_SKU, ASK_TITLE, ASK_DESC, ASK_PRICE, ASK_BOX_COUNT, ASK_BRAND = range(6)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛸 مستعد لتلقي صور منتجات مــنتــجـك وتكويدها تلقائياً مع الكينج MR Bo0!")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    raw_path = "bot_raw.png"
    processed_path = "bot_processed.png"
    await photo_file.download_to_drive(raw_path)
    
    current_text = st.session_state.get("brand_text_input", "Montgk Brand")
    process_product_image(raw_path, processed_path, bottom_text=current_text)
    
    await update.message.reply_photo(photo=open(processed_path, 'rb'), caption="⚡ تم معالجة وحقن الصورة باللوجو النشط والاسم الحالي!")
    
    context.user_data['current_product'] = {}
    await update.message.reply_text("📦 **السؤال 1:** اكتب كود المنتج الفريد (Product SKU)؟")
    return ASK_SKU

async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['sku'] = update.message.text.strip()
    await update.message.reply_text("🏷️ **السؤال 2:** اسم وعنوان المنتج (Product Title)؟")
    return ASK_TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['title'] = update.message.text.strip()
    await update.message.reply_text("📝 **السؤال 3:** وصف ومميزات المنتج (Description)؟")
    return ASK_DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['description'] = update.message.text.strip()
    await update.message.reply_text("💰 **السؤال 4:** كام سعر الشراء / الجملة الإجمالي؟")
    return ASK_PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['original_price'] = int(update.message.text.strip())
        await update.message.reply_text("📦 **السؤال 5:** عدد القطع داخل البوكس أو الدستة؟")
        return ASK_BOX_COUNT
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح للسعر:")
        return ASK_PRICE

async def get_box_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['box_count'] = int(update.message.text.strip())
        await update.message.reply_text("🏭 **السؤال 6:** اسم البراند؟ (أو اكتب /skip لو عام)")
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
    
    # استدعاء دالة التنسيق الملون الفخم مباشرة أثناء الحفظ التلقائي
    save_styled_excel(EXCEL_PATH, new_row)
    
    commercial_post = (
        f"📦 **{prod['title']}**\n🔢 كود المنتج: `{prod['sku']}`\n\n"
        f"💬 {prod['description']}\n\n"
        f"🔥 سعر العرض الخاص من مــنتــجـك: {selling_price} ج!\n"
        f"📌 (سعر القطعة جملة واصل عليك بـ {piece_price} ج بس! 💣)\n\n"
        f"#MR_Bo0\n#Montgk-منتجك"
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
    app.run_polling()

if HAS_TELEGRAM and "bot_thread_started" not in st.session_state and TOKEN != "":
    st.session_state["bot_thread_started"] = True
    threading.Thread(target=run_bot_loop, daemon=True).start()

# ==================== 💻 واجهة العرض الرئيسية والجدول المطور ====================
st.subheader("📊 كتالوج وجدول منتجات أمازون والمنصات الموحد")

test_input = st.text_area("أدخل نص كشط المنتج لتجربة الفحص الذكي والترتيب اللغوي:")
if test_input:
    parsed_price, parsed_box = advanced_smart_parse(test_input)
    st.write(f"🔍 السعر الملقوط: **{parsed_price} ج** | 📦 عدد القطع: **{parsed_box}**")
    chosen_orig_price = st.number_input("💵 السعر الأصلي للمنتج:", min_value=0, max_value=1000000, value=int(parsed_price))

if os.path.exists(EXCEL_PATH):
    try:
        # قراءة البيانات النظيفة وعرضها على لوحة التحكم بدون التوقيع الجمالي لعدم تشويه مظهر الجدول البرمجي
        df_display = pd.read_excel(EXCEL_PATH)
        df_clean = df_display[df_display.iloc[:, 0].astype(str).str.contains("🛸") == False]
        st.dataframe(df_clean, use_container_width=True)
    except:
        st.info("📊 الجدول يتم تهيئته الآن واستقبال البيانات الفخمة...")

st.markdown("<br><p style='text-align: center; color: #2a4d69; font-weight: bold;'>🛸 تم التطوير والأداء بكل فخامة بواسطة: MR Bo0 🛸</p>", unsafe_allow_html=True)
if not os.path.exists(EXCEL_PATH):
    pd.DataFrame(columns=["sku", "title", "standard_price", "brand_name", "description", "piece_price", "original_price"]).to_excel(EXCEL_PATH, index=False)

# --- 🎯 محرك الترتيب الذكي اللغوي المطور ---
def advanced_smart_parse(text):
    clean_text = re.sub(r'01[0125]\d{8}', '', text)
    clean_text = clean_text.replace("2026", "").replace("2025", "")
    
    # 1. لقط عدد الدستة من النص
    box_count = None
    for kw in config.DOZEN_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            box_count = int(match.group(1) or match.group(2))
            break
    if not box_count or box_count == 0:
        box_count = 12

    # 2. لقط السعر الإجمالي
    total_price = None
    for kw in config.PRICE_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            total_price = int(match.group(1) or match.group(2))
            break

    # 3. تعديل ذكي: لو لقط "سعر القطعة" نصلح الحسبة الإجمالية فوراً
    if "سعر القطعة" in clean_text or "سعر القطعه" in clean_text:
        p_match = re.search(r'(?:سعر القطع[ةه]\s*[:\-=\s]*\s*(\d+))|(\d+)\s*سعر القطع[ةه]', clean_text)
        if p_match:
            piece_val = int(p_match.group(1) or p_match.group(2))
            if total_price == piece_val or not total_price:
                total_price = piece_val * box_count

    if not total_price:
        total_price = 0

    return total_price, box_count

# --- دالة حقن ومعالجة الصور باللوجو المخصص والاسم السفلي المتغير ---
def process_product_image(in_path, out_path, bottom_text="Montgk Brand"):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    
    # تأثير عزل الخلفية (Blur) الاحترافي الحصري لـ مــنتــجـك
    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.composite(img, blurred_img, mask)

    # دمج اللوجو الحالي النشط
    if os.path.exists(ACTIVE_LOGO_PATH):
        logo = Image.open(ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w*0.25), int(h*0.15)))
        img.paste(logo, (w - logo.size[0] - 15, 15), logo)
        
    # طباعة الاسم المتغير أسفل الصورة
    draw_obj = ImageDraw.Draw(img)
    try:
        draw_obj.text((20, h - 40), bottom_text, fill=(255, 255, 255, 200))
    except: pass
    img.save(out_path, "PNG")

# ==================== 🛠️ لوحة التحكم الجانبية (الأزار واللوجو المتغير) ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛸 تحكم مــنتــجـك VIP</h2>", unsafe_allow_html=True)
    
    st.markdown("### 🖼️ لوحة تغيير اللوجو")
    new_logo = st.file_uploader("ارفع أو الصق لوجو جديد هنا:", type=["png", "jpg", "jpeg"])
    if new_logo is not None:
        Image.open(new_logo).save(ACTIVE_LOGO_PATH)
        st.success("✅ تم تحديث اللوجو بنجاح في السيرفر!")
        
    if st.button("🔄 إزالة اللوجو المخصص (الرجوع للأصلي)"):
        Image.open(DEFAULT_LOGO_PATH).save(ACTIVE_LOGO_PATH)
        st.success("🔄 تم استعادة اللوجو الافتراضي بنجاح!")
        st.rerun()
        
    st.write("---")
    st.markdown("### 📝 نص البراند السفلي")
    if "brand_text_input" not in st.session_state:
        st.session_state["brand_text_input"] = "Montgk Brand"
    b_text = st.text_input("تعديل النص المطبوع على الصورة:", value=st.session_state["brand_text_input"])
    if b_text != st.session_state["brand_text_input"]:
        st.session_state["brand_text_input"] = b_text
        st.success("📝 تم تعديل الاسم بنجاح!")

# ==================== 🛰️ محرك البوت الذكي التلقائي (التليجرام) ====================
ASK_SKU, ASK_TITLE, ASK_DESC, ASK_PRICE, ASK_BOX_COUNT, ASK_BRAND = range(6)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛸 مستعد لتلقي صور منتجات مــنتــجـك وتكويدها تلقائياً!")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    raw_path = "bot_raw.png"
    processed_path = "bot_processed.png"
    await photo_file.download_to_drive(raw_path)
    
    current_text = st.session_state.get("brand_text_input", "Montgk Brand")
    process_product_image(raw_path, processed_path, bottom_text=current_text)
    
    await update.message.reply_photo(photo=open(processed_path, 'rb'), caption="⚡ تم معالجة وحقن الصورة باللوجو النشط والاسم الحالي!")
    
    context.user_data['current_product'] = {}
    await update.message.reply_text("📦 **السؤال 1:** اكتب كود المنتج الفريد (Product SKU)؟")
    return ASK_SKU

async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['sku'] = update.message.text.strip()
    await update.message.reply_text("🏷️ **السؤال 2:** اسم وعنوان المنتج (Product Title)؟")
    return ASK_TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['title'] = update.message.text.strip()
    await update.message.reply_text("📝 **السؤال 3:** وصف ومميزات المنتج (Description)؟")
    return ASK_DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['description'] = update.message.text.strip()
    await update.message.reply_text("💰 **السؤال 4:** كام سعر الشراء / الجملة الإجمالي؟")
    return ASK_PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['original_price'] = int(update.message.text.strip())
        await update.message.reply_text("📦 **السؤال 5:** عدد القطع داخل البوكس أو الدستة؟")
        return ASK_BOX_COUNT
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح للسعر:")
        return ASK_PRICE

async def get_box_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['box_count'] = int(update.message.text.strip())
        await update.message.reply_text("🏭 **السؤال 6:** اسم البراند؟ (أو اكتب /skip لو عام)")
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
        f"📌 (سعر القطعة جملة واصل عليك بـ {piece_price} ج بس! 💣)\n\n"
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
    app.run_polling()

if HAS_TELEGRAM and "bot_thread_started" not in st.session_state and TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    st.session_state["bot_thread_started"] = True
    threading.Thread(target=run_bot_loop, daemon=True).start()

# ==================== 💻 واجهة العرض الرئيسية ونموذج الفحص المحمي من الانهيار ====================
st.subheader("📊 كتالوج وجدول منتجات أمازون والمنصات الموحد")

test_input = st.text_area("أدخل نص كشط المنتج لتجربة الفحص الذكي والترتيب اللغوي:")
if test_input:
    parsed_price, parsed_box = advanced_smart_parse(test_input)
    st.write(f"🔍 السعر الملقوط: **{parsed_price} ج** | 📦 عدد الدستة/القطع: **{parsed_box}**")
    
    # حماية عناصر الإدخال اليدوية بمدى واسع جداً وآمن ومفتوح
    chosen_orig_price = st.number_input("💵 السعر الأصلي للمنتج:", min_value=0, max_value=1000000, value=int(parsed_price))

if os.path.exists(EXCEL_PATH):
    df_current = pd.read_excel(EXCEL_PATH)
    st.dataframe(df_current, use_container_width=True)
# --- 🎯 محرك الفحص والترتيب اللغوي المنصوح والمطور ---
def advanced_smart_parse(text):
    clean_text = re.sub(r'01[0125]\d{8}', '', text)
    clean_text = clean_text.replace("2026", "").replace("2025", "")
    
    # 1. التقاط عدد الدستة
    box_count = None
    for kw in config.DOZEN_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            box_count = int(match.group(1) or match.group(2))
            break
    if not box_count:
        box_count = 12

    # 2. التقاط السعر الإجمالي
    total_price = None
    for kw in config.PRICE_KEYWORDS:
        pattern = r'(?:' + re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+))|(\d+)\s*' + re.escape(kw)
        match = re.search(pattern, clean_text)
        if match:
            total_price = int(match.group(1) or match.group(2))
            break

    # 3. معالجة "سعر القطعة" المصحح وعكس الحسبة الذكية
    if "سعر القطعة" in clean_text or "سعر القطعه" in clean_text:
        p_match = re.search(r'(?:سعر القطع[ةه]\s*[:\-=\s]*\s*(\d+))|(\d+)\s*سعر القطع[ةه]', clean_text)
        if p_match:
            piece_val = int(p_match.group(1) or p_match.group(2))
            if total_price == piece_val or not total_price:
                total_price = piece_val * box_count

    if not total_price:
        total_price = 0

    return total_price, box_count

# --- دالة حقن ومعالجة الصور باللوجو والنص المتغير ---
def process_product_image(in_path, out_path, bottom_text="Montgk Brand"):
    img = Image.open(in_path).convert("RGBA")
    w, h = img.size
    
    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.composite(img, blurred_img, mask)

    if os.path.exists(ACTIVE_LOGO_PATH):
        logo = Image.open(ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w*0.25), int(h*0.15)))
        img.paste(logo, (w - logo.size[0] - 15, 15), logo)
        
    draw_obj = ImageDraw.Draw(img)
    try:
        draw_obj.text((20, h - 40), bottom_text, fill=(255, 255, 255, 200))
    except: pass
    img.save(out_path, "PNG")

# ==================== 🛠️ لوحة التحكم الجانبية المتفخمة ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛸 تحكم مــنتــجـك VIP</h2>", unsafe_allow_html=True)
    
    st.markdown("### 🖼️ لوحة تغيير اللوجو")
    new_logo = st.file_uploader("ارفع لوجو جديد هنا:", type=["png", "jpg", "jpeg"])
    if new_logo is not None:
        Image.open(new_logo).save(ACTIVE_LOGO_PATH)
        st.success("✅ تم تحديث اللوجو بنجاح في السيرفر!")
        
    if st.button("🔄 إزالة اللوجو المخصص (الرجوع للأصلي)"):
        Image.open(DEFAULT_LOGO_PATH).save(ACTIVE_LOGO_PATH)
        st.success("🔄 تم استعادة اللوجو الأصلي!")
        st.rerun()
        
    st.write("---")
    st.markdown("### 📝 نص البراند السفلي")
    if "brand_text_input" not in st.session_state:
        st.session_state["brand_text_input"] = "Montgk Brand"
    b_text = st.text_input("تعديل النص المطبوع:", value=st.session_state["brand_text_input"])
    if b_text != st.session_state["brand_text_input"]:
        st.session_state["brand_text_input"] = b_text
        st.success("📝 تم تعديل الاسم بنجاح!")

# ==================== 🛰️ محرك البوت الذكي التلقائي ====================
ASK_SKU, ASK_TITLE, ASK_DESC, ASK_PRICE, ASK_BOX_COUNT, ASK_BRAND = range(6)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛸 مرحب بيك في رادار مــنتــجـك! ابعت الصورة وهقوم بتجهيز كل شيء أوتوماتيك.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    raw_path = "bot_raw.png"
    processed_path = "bot_processed.png"
    await photo_file.download_to_drive(raw_path)
    
    # المعالجة التلقائية وفلترة الصورة فوراً قبل بدء الأسئلة
    current_text = st.session_state.get("brand_text_input", "Montgk Brand")
    process_product_image(raw_path, processed_path, bottom_text=current_text)
    
    # إرسال الصورة المعدلة فوراً للمستخدم باللوجو الجديد
    await update.message.reply_photo(photo=open(processed_path, 'rb'), caption="⚡ تم معالجة وحقن اللوجوهات والأسماء بنجاح!")
    
    context.user_data['current_product'] = {}
    await update.message.reply_text("📦 **السؤال 1:** اكتب كود المنتج الفريد (Product SKU)؟")
    return ASK_SKU

# (باقي خطوات تعبئة الداتا لملف الإكسيل والبوست)
async def get_sku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['sku'] = update.message.text.strip()
    await update.message.reply_text("🏷️ **السؤال 2:** اسم وعنوان المنتج (Product Title)؟")
    return ASK_TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['title'] = update.message.text.strip()
    await update.message.reply_text("📝 **السؤال 3:** وصف ومميزات المنتج (Description)؟")
    return ASK_DESC

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_product']['description'] = update.message.text.strip()
    await update.message.reply_text("💰 **السؤال 4:** كام سعر الشراء / الجملة الإجمالي؟")
    return ASK_PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['original_price'] = int(update.message.text.strip())
        await update.message.reply_text("📦 **السؤال 5:** عدد القطع داخل البوكس أو الدستة؟")
        return ASK_BOX_COUNT
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح للسعر:")
        return ASK_PRICE

async def get_box_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_product']['box_count'] = int(update.message.text.strip())
        await update.message.reply_text("🏭 **السؤال 6:** البراند؟ (أو /skip لو عام)")
        return ASK_BRAND
    except:
        await update.message.reply_text("⚠️ اكتب رقم صحيح للقطع:")
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
        f"📌 (القطعة جملة واقفة عليك بـ {piece_price} ج بس! 💣)\n\n"
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
    app.run_polling()

if HAS_TELEGRAM and "bot_thread_started" not in st.session_state and TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    st.session_state["bot_thread_started"] = True
    threading.Thread(target=run_bot_loop, daemon=True).start()

# ==================== 💻 واجهة العرض الرئيسية لـ Streamlit ====================
if not HAS_TELEGRAM:
    st.error("⚠️ مكتبة التليجرام مش متثبتة على السيرفر! يرجى تحديث ملف requirements.txt فوراً.")

st.subheader("📊 كتالوج وجدول منتجات أمازون والمنصات الموحد")
if os.path.exists(EXCEL_PATH):
    df_current = pd.read_excel(EXCEL_PATH)
    st.dataframe(df_current, use_container_width=True)    img.save(DEFAULT_LOGO_PATH)
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
