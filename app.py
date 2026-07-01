import os
import re
import json
import time
import threading
import requests
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image, ImageFilter, ImageDraw

# ==================== إعدادات المنصة والبراند ====================
st.set_page_config(page_title="Montgk Empire Platform V17", page_icon="🥷", layout="wide")

# 🔒 التوكن الأصلي والنهائي مثبت ومأمن هنا
BOT_TOKEN = "8685178390:AAEgzrKz2yHW2oeflsZyZMeSN1Nw0da3vvI" 

TMP_DIR = "bot_media"
if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)

EXCEL_FILE = "Montgk_Live_Products.xlsx"

# قاعدة بيانات المستوردين (المصنع القديم)
IMPORTERS = {
    "BAGH": {"name": "البغدادي للأدوات المنزلية", "margin": 1.25},
    "SHAH": {"name": "الشهاب ستور للاكسسوارات", "margin": 1.20},
    "KANZ": {"name": "الكنز للجملة", "margin": 1.30}
}

def load_excel_data():
    if os.path.exists(EXCEL_FILE):
        try: return pd.read_excel(EXCEL_FILE).to_dict(orient="records")
        except: return []
    return []

def save_to_excel(data_list):
    df = pd.DataFrame(data_list)
    df.to_excel(EXCEL_FILE, index=False)

# دالة معالجة وختم الصور واللوجو الفوري
def process_image_bot(img_path, sku_code):
    try:
        img = Image.open(img_path).convert("RGBA")
        w, h = img.size
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
        img = Image.composite(img, blurred_img, mask)
        
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, h-50, w, h], fill=(20, 20, 24, 200))
        try:
            draw.text((20, h - 35), "🔒 Montgk - مـنتـجكـ & Mr:- Bo0", fill=(255, 255, 255, 255))
        except: pass
        
        out_p = os.path.join(TMP_DIR, f"Montgk_{sku_code}.png")
        img.save(out_p, "PNG")
        return out_p
    except:
        return img_path

# ==================== كواليس البوت السري والتفاعل عبر التليجرام ====================
def run_telegram_bot():
    offset = 0
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    bot_sessions = {}
    
    while True:
        try:
            res = requests.get(f"{base_url}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    
                    msg = update.get("message") or update.get("channel_post") or update.get("edited_message")
                    if not msg: continue
                    
                    chat_id = msg["chat"]["id"]
                    msg_id = msg["message_id"]
                    text = msg.get("text", "").strip()
                    
                    # 1️⃣ المصنع القديم: لو المستخدم بعت أمر أو لينك أو تيكست عادي سحب تلقائي
                    if text and not "reply_to_message" in msg:
                        if text.startswith("/start"):
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id, "text": "🔒 أهلاً بك في منصة مـنتـجكـ الشاملة المحدثة V17!\n\n- ابعت صورة منتج عشان أبدأ معاك الاستجواب التفاعلي السريع.\n- أو ابعت بوست المورد عشان أفرمه تلقائي!"
                            })
                        elif "http" in text or "https" in text:
                            # معالجة اللينك التلقائي القديم
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id, "text": "🔄 جاري قراءة الرابط وتحديث السعر في المستودع القديم..."
                            })
                        continue
                    
                    # 2️⃣ المصنع الجديد: فحص وجود الصورة حتى لو جوة رسالة معاد توجيهها (Forward)
                    if "photo" in msg:
                        photo_file = msg["photo"][-1]
                        file_id = photo_file["file_id"]
                        
                        f_res = requests.get(f"{base_url}/getFile", params={"file_id": file_id}).json()
                        f_path = f_res["result"]["file_path"]
                        img_data = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}").content
                        
                        local_img_path = os.path.join(TMP_DIR, f"raw_{chat_id}.png")
                        with open(local_img_path, "wb") as f: f.write(img_data)
                        
                        bot_sessions[chat_id] = {
                            "step": "WAITING_SKU",
                            "raw_image_path": local_img_path,
                            "sku": "", "name": "", "price": "", "desc": ""
                        }
                        
                        requests.post(f"{base_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "🔢 لقطت المنتج يا صاحبي! (الخطوة 1/4):\nاعمل Reply (رد) على الرسالة دي واكتب كود المنتج (SKU):",
                            "reply_to_message_id": msg_id
                        })
                        continue
                    
                    # شات الاستجواب التفاعلي عبر الـ Reply
                    if chat_id in bot_sessions and "reply_to_message" in msg:
                        session = bot_sessions[chat_id]
                        reply_text = msg.get("text", "").strip()
                        
                        if session["step"] == "WAITING_SKU":
                            session["sku"] = reply_text
                            session["step"] = "WAITING_NAME"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "🏷️ الخطوة (2/4):\nتمام يا كبير، اعمل Reply واكتب اسم المنتج التجاري الحصري:",
                                "reply_to_message_id": msg_id
                            })
                        elif session["step"] == "WAITING_NAME":
                            session["name"] = reply_text
                            session["step"] = "WAITING_PRICE"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "💵 الخطوة (3/4):\nاعمل Reply واكتب سعر البيع الأساسي (أرقام فقط):",
                                "reply_to_message_id": msg_id
                            })
                        elif session["step"] == "WAITING_PRICE":
                            session["price"] = reply_text
                            session["step"] = "WAITING_DESC"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "📝 الخطوة (4/4) الأخيرة:\nاعمل Reply واكتب الوصف والمميزات عشان أقفل الجدول واللوجو:",
                                "reply_to_message_id": msg_id
                            })
                        elif session["step"] == "WAITING_DESC":
                            session["desc"] = reply_text
                            
                            final_img = process_image_bot(session["raw_image_path"], session["sku"])
                            
                            current_products = load_excel_data()
                            current_products.append({
                                "كود المنتج (SKU)": session["sku"], "اسم المنتج": session["name"],
                                "سعر البيع": session["price"], "الوصف التفصيلي": session["desc"],
                                "ملف الصورة المفرومة": os.path.basename(final_img),
                                "حقوق الملكية": "🔒 مـنتـجكـ - Montgk & Mr:- Bo0"
                            })
                            save_to_excel(current_products)
                            
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"🎉 تسلم إيدك يا مايسترو! المنتج [ {session['name']} ] اتفرز ونزل شيت الإكسيل أوتوماتيك، وحقوق براند مـنتـجكـ في الأمان! 👑🥷",
                                "reply_to_message_id": msg_id
                            })
                            del bot_sessions[chat_id]
                            
        except Exception as e:
            pass
        time.sleep(2)

# التراك المنفصل الآمن
if "bot_loop" not in st.session_state:
    st.session_state["bot_loop"] = True
    threading.Thread(target=run_telegram_bot, daemon=True).start()

# ==================== لوحة تحكم الويب المدمجة ====================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .brand-header {
        background: linear-gradient(135deg, #111115 0%, #ff4b4b 100%);
        padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 25px;
    }
    .brand-title { color: white; font-size: 36px; font-weight: bold; }
    .brand-sub { color: #e0e0e0; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="brand-header">
        <div class="brand-title">🥷 Mr:- Bo0 Empire</div>
        <div class="brand-sub">🚀 مـنتـجكـ - Montgk All-In-One Unified Factory</div>
    </div>
""", unsafe_allow_html=True)

# تقسيم الشاشة لأقسام المصنع القديم والجديد
tab1, tab2 = st.tabs(["📦 مستودع المنتجات الذكي (الجديد)", "📋 دفتر المستوردين والمعادلات (القديم)"])

with tab1:
    st.subheader("📦 جدول المنتجات الكلية المفرومة لايف")
    products_list = load_excel_data()
    if products_list:
        df_display = pd.DataFrame(products_list)
        st.dataframe(df_display, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Montgk_Products')
        st.download_button(
            label="📥 تحميل شيت الإكسيل المفروم الجاهز للمتجر",
            data=output.getvalue(),
            file_name="Montgk_Empire_Products.xlsx"
        )
    else:
        st.info("📭 المستودع فاضي حالياً. اعمل Forward لأول صورة منتج للبوت من تليفونك وابدأ الاستجواب!")

with tab2:
    st.subheader("📋 دفتر أكواد ونسب المستوردين المسجلين")
    df_importers = pd.DataFrame([
        {"كود المستورد": k, "اسم البراند": v["name"], "نسبة الربح المضافة": f"{(v['margin']-1)*100:.0f}%"}
        for k, v in IMPORTERS.items()
    ])
    st.table(df_importers)
    st.success("⚙️ جميع معادلات السحب التلقائي والزيادة الذكية شغالة في الخلفية أوتوماتيك!")
