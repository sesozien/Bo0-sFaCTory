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
st.set_page_config(page_title="Bo0's Interactive Bot V13", page_icon="🥷", layout="centered")

# 🚨 حط التوكن الحقيقي بتاعك هنا عشان البوت يشتغل لايف فوري
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE" 

# واجهة Streamlit الشيك
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
        <div class="brand-title">🥷 Mr:- Bo0</div>
        <div class="brand-sub">🚀 مـنتـجكـ - Montgk Ultimate Interactive Bot</div>
    </div>
""", unsafe_allow_html=True)

TMP_DIR = "bot_media"
if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)

EXCEL_FILE = "Montgk_Live_Products.xlsx"

# دالة لقراءة الجدول الحالي أو إنشاء واحد جديد
def load_excel_data():
    if os.path.exists(EXCEL_FILE):
        try: return pd.read_excel(EXCEL_FILE).to_dict(orient="records")
        except: return []
    return []

def save_to_excel(data_list):
    df = pd.DataFrame(data_list)
    df.to_excel(EXCEL_FILE, index=False)

# مخزن مؤقت في الذاكرة لحفظ حالة الاستجواب لكل مستخدم (حسب الـ Chat ID)
if "bot_sessions" not in st.session_state:
    st.session_state["bot_sessions"] = {}

# دالة معالجة وختم الصور
def process_image_bot(img_path, sku_code):
    try:
        img = Image.open(img_path).convert("RGBA")
        w, h = img.size
        # تأثير الـ Blur الاحترافي لعزل الخلفية
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
        img = Image.composite(img, blurred_img, mask)
        
        # كتابة الحقوق براند مـنتـجكـ
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, h-50, w, h], fill=(20, 20, 24, 200))
        try:
            draw.text((20, h - 35), "🔒 Montgk - مـنتـجكـ & Mr:- Bo0", fill=(255, 255, 255, 255))
        except: pass
        
        out_p = os.path.join(TMP_DIR, f"Montgk_{sku_code}.png")
        img.save(out_p, "PNG")
        return out_p
    except Exception as e:
        return img_path

# ==================== كواليس البوت السري والتفاعل عبر التليجرام ====================
def run_telegram_bot():
    offset = 0
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    while True:
        try:
            res = requests.get(f"{base_url}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message") or update.get("channel_post")
                    if not msg: continue
                    
                    chat_id = msg["chat"]["id"]
                    msg_id = msg["message_id"]
                    sessions = st.session_state["bot_sessions"]
                    
                    # 1️⃣ الحالة الأولى: المستخدم بعت صورة منتج جديدة
                    if "photo" in msg:
                        photo_file = msg["photo"][-1]  # أعلى جودة
                        file_id = photo_file["file_id"]
                        
                        # تحميل الصورة وحفظها مؤقتاً
                        f_res = requests.get(f"{base_url}/getFile", params={"file_id": file_id}).json()
                        f_path = f_res["result"]["file_path"]
                        img_data = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_path}").content
                        
                        local_img_path = os.path.join(TMP_DIR, f"raw_{chat_id}.png")
                        with open(local_img_path, "wb") as f: f.write(img_data)
                        
                        # فتح جلسة استجواب جديدة للمستند ده
                        sessions[chat_id] = {
                            "step": "WAITING_SKU",
                            "raw_image_path": local_img_path,
                            "sku": "", "name": "", "price": "", "desc": ""
                        }
                        
                        # إرسال سؤال الـ SKU
                        requests.post(f"{base_url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "🔢 الخطوة (1/4):\nمن فضلك اعمل Reply (رد) على الرسالة دي واكتب كود المنتج (SKU):",
                            "reply_to_message_id": msg_id
                        })
                        continue
                    
                    # 2️⃣ الحالة الثانية: المستخدم بيرد (Reply) على أسئلة البوت
                    if chat_id in sessions and "reply_to_message" in msg:
                        session = sessions[chat_id]
                        reply_text = msg.get("text", "").strip()
                        
                        if session["step"] == "WAITING_SKU":
                            session["sku"] = reply_text
                            session["step"] = "WAITING_NAME"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "🏷️ الخطوة (2/4):\nتمام يا صاحبي، اعمل Reply واكتب اسم المنتج التجاري المعتمد:",
                                "reply_to_message_id": msg_id
                            })
                            
                        elif session["step"] == "WAITING_NAME":
                            session["name"] = reply_text
                            session["step"] = "WAITING_PRICE"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "💵 الخطوة (3/4):\nاعمل Reply واكتب سعر البيع النهائي (أرقام فقط):",
                                "reply_to_message_id": msg_id
                            })
                            
                        elif session["step"] == "WAITING_PRICE":
                            session["price"] = reply_text
                            session["step"] = "WAITING_DESC"
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "📝 الخطوة (4/4) الأخيرة:\nاعمل Reply واكتب الوصف التفصيلي أو المميزات للمنتج:",
                                "reply_to_message_id": msg_id
                            })
                            
                        elif session["step"] == "WAITING_DESC":
                            session["desc"] = reply_text
                            
                            # 🛠️ معالجة الصورة وفك الشفرات وحفظ السطر في الإكسيل
                            final_img = process_image_bot(session["raw_image_path"], session["sku"])
                            
                            current_products = load_excel_data()
                            current_products.append({
                                "كود المنتج (SKU)": session["sku"],
                                "اسم المنتج": session["name"],
                                "سعر البيع": session["price"],
                                "الوصف التفصيلي": session["desc"],
                                "ملف الصورة المفرومة": os.path.basename(final_img),
                                "حقوق الملكية": "🔒 مـنتـجكـ - Montgk & Mr:- Bo0"
                            })
                            save_to_excel(current_products)
                            
                            # ختم الاستجواب بنجاح ساحق
                            requests.post(f"{base_url}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": f"🎉 تسلم إيدك يا مايسترو! المنتج [ {session['name']} ] اتفرز واتقشر ودخل شيت الإكسيل أوتوماتيك، وحقوق براند مـنتـجكـ في الأمان! 👑🥷",
                                "reply_to_message_id": msg_id
                            })
                            # إغلاق الجلسة بنجاح
                            del sessions[chat_id]
                            
        except Exception as e:
            time.sleep(2)

# تشغيل تراك البوت السري في thread منفصل عشان السيرفر يفضل صاحي
if "bot_thread_started" not in st.session_state:
    st.session_state["bot_thread_started"] = True
    t = threading.Thread(target=run_telegram_bot, daemon=True)
    t.start()

# ==================== لوحة تحكم الويب لرؤية وتحميل الإكسيل ====================
st.subheader("📦 مستودع المنتجات الحالي (تحديث لحظي من البوت السري)")

products_list = load_excel_data()
if products_list:
    df_display = pd.DataFrame(products_list)
    st.dataframe(df_display)
    
    # زرار التحميل الفوري
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False, sheet_name='Montgk_Products')
    st.download_button(
        label="📥 تحميل شيت الإكسيل المفروم الجاهز للمتجر",
        data=output.getvalue(),
        file_name="Montgk_Empire_Products.xlsx"
    )
else:
    st.info("📭 المستودع فاضي حالياً. ابعت أول صورة منتج للبوت السري من تليفونك وابدأ الاستجواب!")
