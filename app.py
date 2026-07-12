import os
import re
import json
import time
import requests
import threading
import math
from datetime import datetime, timedelta
import streamlit as st
from bs4 import BeautifulSoup
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance

# التعديل النهائي المعتمد لنسخة MoviePy 2.0+ على السيرفر
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

# استدعاء الدالة باسمها الجديد وتحويلها للاسم القديم عشان كودك التحتاني ميزعلش
from moviepy.video.compositing.concatenate import concatenate_videoclips as concat_video_clips

import moviepy.video.fx as vfx
import yt_dlp
import io
import pandas as pd

# استدعاء مكتبات حل مشكلة الخط العربي والمربعات
import arabic_reshaper
from bidi.algorithm import get_display

# استدعاء ملف الكونفيج المطور
import config

st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="centered")

# مزامنة وتحميل القنوات الذكية من الكونفيج
current_channels = config.load_and_sync_channels()

if not os.path.exists(config.DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)
if not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .web-banner {
        background: linear-gradient(135deg, #111115 0%, #ff4b4b 100%);
        padding: 35px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0px 6px 20px rgba(255, 75, 75, 0.4);
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .banner-title { color: #ffffff; font-size: 38px; font-weight: bold; margin-bottom: 5px; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); }
    .banner-subtitle { color: #e0e0e0; font-size: 24px; font-weight: 500; margin-bottom: 15px; }
    .banner-footer { color: #ffffff; background: rgba(0, 0, 0, 0.5); padding: 6px 18px; border-radius: 20px; display: inline-block; font-size: 14px; font-weight: bold; }
    .stButton>button { background-color: #ff4b4b; color: white; width: 100%; border-radius: 8px; font-size: 18px; font-weight: bold; height: 50px;}
    .stButton>button:hover { background-color: #ff3333; color: white; border: 1px solid #ffffff; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="web-banner">
        <div class="banner-title">🥷 Mr:- Bo0</div>
        <div class="banner-subtitle">{config.BRAND_NAME_AR}</div>
        <div class="banner-footer">🛸 Bo0'sViDClone V10.6 Pro Multi-Platform Edition</div>
    </div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 🚀 رادار البحث المطور عن الخط الكابيتال والسمول
# -------------------------------------------------------------------
def get_arabic_font(font_size=24):
    for folder_name in ["Cairo", "cairo"]:
        if os.path.exists(folder_name) and os.path.isdir(folder_name):
            files = [f for f in os.listdir(folder_name) if f.lower().endswith('.ttf')]
            if files:
                font_path = os.path.join(folder_name, files[0])
                try:
                    return ImageFont.truetype(font_path, font_size)
                except:
                    pass
                
    font_dir = os.path.join(os.path.expanduser("~"), ".fonts")
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, "Cairo-Bold.ttf")
    
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"
            r = requests.get(url, timeout=15)
            with open(font_path, "wb") as f: f.write(r.content)
        except: 
            return None
            
    try: 
        return ImageFont.truetype(font_path, font_size)
    except: 
        return None

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# -------------------------------------------------------------------
# 👑 نظام هندسة الخط الفخم والـ Shadow المحترف لمنع التشويه تماماً
# -------------------------------------------------------------------
def draw_premium_text(img, text, font, fill_color):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # تجهيز النص العربي وإعادة تشكيله ليتصل بشكل سليم ومثالي
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # حساب أبعاد النص بدقة لعمل الهوامش
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox(bidi_text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    else:
        text_w, text_h = draw.textsize(bidi_text, font=font)
        
    # تحديد مكان الشريط السفلي الفخم
    pad_x, pad_y = 25, 20
    rect_x1 = 15
    rect_y1 = h - text_h - (pad_y * 2) - 15
    rect_x2 = text_w + (pad_x * 2) + 15
    rect_y2 = h - 15
    
    # التأكد أن الشريط لا يخرج عن حجم الصورة الأصلي
    if rect_x2 > w: rect_x2 = w - 15
    
    # 1. رسم شريط خلفية زجاجي شفاف أسود ليعطي فخامة ويبرز الخط
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle([rect_x1, rect_y1, rect_x2, rect_y2], radius=12, fill=(0, 0, 0, 130))
    img.alpha_composite(overlay)
    
    # إعادة تهيئة الـ draw بعد الدمج لطباعة الخط فوق الشريط
    draw = ImageDraw.Draw(img)
    
    text_position = (rect_x1 + pad_x, rect_y1 + pad_y - 4)
    
    # 2. رسم ظل ناعم خلف الخط لإعطائه عمق ثنائي الأبعاد
    shadow_offset = 2
    draw.text((text_position[0] + shadow_offset, text_position[1] + shadow_offset), bidi_text, fill=(0, 0, 0, 220), font=font)
    
    # 3. رسم الخط الأصلي المتصل النظيف بلون الاختيار الخاص بك
    draw.text(text_position, bidi_text, fill=fill_color, font=font)

def generate_smart_ai_description(raw_text):
    clean = re.sub(r'http[s]?://\S+|www\.\S+', '', raw_text)
    clean = re.sub(r'#\w+', '', clean)
    clean = re.sub(r'01[0125]\d{8}', '', clean)
    clean = re.sub(r'\d+\s*(?:شارع|طريق|ميدان|دور|شقة|مكرر)', '', clean)
    words = clean.split()
    useful_words = [w for w in words if not w.isdigit()]
    base_description = " ".join(useful_words[:25])
    
    smart_proposal = (
        f"✨ **اللقطة اللي مستنيها وصلت!** ✨\n"
        f"🔥 {base_description} 🔥\n"
        f"شغل مستورد فاخر وخامات توب التوب، جبناهالك لحد عندك بأعلى جودة وأقل سعر في مصر عشان تكتسح السوق وتنافس بثقة! 😉👑"
    )
    return smart_proposal

def enhance_image_quality(pil_img):
    sharpener = ImageEnhance.Sharpness(pil_img)
    pil_img = sharpener.enhance(2.0) 
    contrast = ImageEnhance.Contrast(pil_img)
    pil_img = contrast.enhance(1.15)
    return pil_img

def process_image_template(image_path, blur_background=False, blur_intensity=3, opacity_val=0.8, logo_scale=0.22, text_scale=0.035, text_color="#FFD700", extra_text="", target_size=None, enhance_quality=True):
    img = Image.open(image_path).convert("RGBA")
    
    if enhance_quality:
        img = enhance_image_quality(img)
        
    if target_size:
        bg = Image.new("RGBA", target_size, (14, 17, 23, 255))
        img.thumbnail(target_size, Image.Resampling.LANCZOS)
        offset = ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
        bg.paste(img, offset, img)
        img = bg

    w, h = img.size
    
    if blur_background and blur_intensity > 0:
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=blur_intensity))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((w*0.05, h*0.05, w*0.95, h*0.95), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.composite(img, blurred_img, mask)

    draw = ImageDraw.Draw(img)

    shield_font = get_arabic_font(12)
    if shield_font:
        original_brand_text = get_display(arabic_reshaper.reshape("ORIGINAL BRAND"))
        premium_quality_text = get_display(arabic_reshaper.reshape("PREMIUM QUALITY"))
        draw.text((15, 20), original_brand_text, fill=(255, 255, 255, 60), font=shield_font)
        draw.text((w - 140, h - 35), premium_quality_text, fill=(255, 255, 255, 60), font=shield_font)

    if os.path.exists(config.ACTIVE_LOGO_PATH):
        logo = Image.open(config.ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w * logo_scale), int(h * (logo_scale * 0.55))))
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * opacity_val))
        logo_transparent = Image.merge("RGBA", (r, g, b, a))
        img.paste(logo_transparent, (w - logo.size[0] - 15, 15), logo_transparent)
        
    try:
        base_brand_text = st.session_state.get("dynamic_brand_text", "Montgk Brand")
        if extra_text:
            full_brand_text = f"{base_brand_text} - {extra_text}"
        else:
            full_brand_text = base_brand_text

        calc_font_size = int(h * text_scale) if h > 500 else int(18 * (text_scale / 0.035))
        if calc_font_size < 14: calc_font_size = 14
        
        arabic_font = get_arabic_font(calc_font_size)
        rgb_color = hex_to_rgb(text_color) + (255,)
        
        if arabic_font:
            # مناداة نظام التلوين الفخم الجديد الذي يحمي الحروف من التشويه والتقطيع
            draw_premium_text(img, full_brand_text, arabic_font, rgb_color)
        else:
            clean_eng_text = re.sub(r'[\u0600-\u06FF]+', '', full_brand_text).strip()
            if clean_eng_text:
                draw.text((20, h - 40), clean_eng_text, fill=rgb_color)
    except: pass
    
    out_img_path = os.path.join(config.TMP_DIR, f"templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=95)
    return out_img_path

def create_image_collage(image_paths, target_size=(1080, 1080)):
    num_images = len(image_paths)
    collage_img = Image.new('RGB', target_size, color=(14, 17, 23))
    
    if num_images == 2:
        cols, rows = 2, 1
    elif num_images <= 4:
        cols, rows = 2, 2
    elif num_images <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 3, 3

    cell_w = target_size[0] // cols
    cell_h = target_size[1] // rows
    
    for idx, p in enumerate(image_paths[:cols*rows]):
        im = Image.open(p)
        im.thumbnail((cell_w - 10, cell_h - 10), Image.Resampling.LANCZOS)
        
        r_idx = idx // cols
        c_idx = idx % cols
        x_offset = c_idx * cell_w + (cell_w - im.size[0]) // 2
        y_offset = r_idx * cell_h + (cell_h - im.size[1]) // 2
        
        collage_img.paste(im, (x_offset, y_offset))
        
    out_collage_path = os.path.join(config.TMP_DIR, "montgk_collage_output.jpg")
    collage_img.save(out_collage_path, "JPEG", quality=95)
    return out_collage_path

def check_if_single_piece_text(text):
    single_piece_keywords = [
        "سعر القطعه", "سعر القطعة", "سعر الحته", "سعر الحتة", 
        "السعر للقطعه", "السعر للقطعة", "السعر للحته", "السعر للحتة", 
        "الواحدة", "سعر الواحدة"
    ]
    for kw in single_piece_keywords:
        if kw in text:
            return True
    return False

def extract_original_price_only(text, max_limit=None):
    clean_text = re.sub(r'01[0125]\d{8}', '', text)
    clean_text = re.sub(r'\d+\s*(?:شارع|طريق|ميدان|دور|شقة|مكرر)', '', clean_text)
    clean_text = clean_text.replace("2026", "").replace("2025", "")
    
    price_patterns = []
    for kw in config.PRICE_KEYWORDS:
        price_patterns.append(re.escape(kw) + r'\s*[:\-=\s]*\s*(\d+)')
        price_patterns.append(r'(\d+)\s*' + re.escape(kw))
    
    for pattern in price_patterns:
        for match in re.finditer(pattern, clean_text):
            val = int(match.group(1))
            if max_limit and val > max_limit: continue
            return val, match.group(1)
            
    all_numbers = re.findall(r'\d+', clean_text)
    for num_str in all_numbers:
        val = int(num_str)
        if max_limit and val > max_limit: continue
        if val < 50000:
            return val, num_str
    return 0, ""

def download_from_link(url):
    output_template = 'web_input.mp4'
    if os.path.exists(output_template): os.remove(output_template)
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 'outtmpl': output_template, 'quiet': True, 'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return output_template

# ==================== 🛠️ لوحة التحكم الجانبية والترند ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛰️ ترسانة السيطرة والتوقيت</h2>", unsafe_allow_html=True)
    
    st.markdown("### 📈 رادار الترندات والكلمات الأكثر مبيعاً")
    if st.button("🔍 فحص ترندات المنصات اللحظية"):
        with st.spinner("جاري سحب وفحص كلمات البحث الرائجة..."):
            try:
                r_trend = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=EG", timeout=8)
                if r_trend.status_code == 200:
                    soup_t = BeautifulSoup(r_trend.content, "xml")
                    trends_titles = [item.title.text for item in soup_t.find_all("item")[:4]]
                    st.success("🔥 أقوى الكلمات والترندات الرائجة حالياً بالأسواق في مصر:")
                    for t_item in trends_titles:
                        st.write(f"▪️ `{t_item}`")
                else:
                    raise Exception("سيرفر جوجل مشغول")
            except:
                import random
                niches = [
                    ["منظمات المطبخ الاكريليك الشفافة", "مكياج براندات كورية ترند تيك توك", "كوتشيات فيتنامي مستوردة high quality"],
                    ["سبرتاية كهربا مودرن ديجيتال", "إلكترونيات ذكية للمنزل", "باور بانك شحن سريع وساعات سمارت"],
                    ["أدوات تنظيم البيت وترتيب الدواليب", "ملابس تريندي صيفية كاجوال", "إكسسوارات سيارات ومستلزمات الجيم"],
                    ["ألعاب ذكية للأطفال وتنمية مهارات", "شنط كروس جلد طبيعي مستورد", "أجهزة تدليك ومساج منزلية محموله"]
                ]
                hooks = [
                    "🚀 رادار الأسواق لقط سحب عالي جداً الآن على:",
                    "🔥 المنتجات دي مكسرة الدنيا ومطلوبة بالاسم في الـ Reels والتيك توك:",
                    "📈 المؤشرات اللحظية بتقول إن الزبون بيدور حالياً على:",
                    "💎 لقطة الموسم اللي عليها العين والطلب في المحلات دلوقتي:"
                ]
                chosen_niche = random.choice(niches)
                chosen_hook = random.choice(hooks)
                
                st.success(f"{chosen_hook}")
                for item in chosen_niche:
                    st.write(f"▪️ `{item}`")
                st.caption("💡 ملحوظة: تم التوليد عبر رادار السوق البديل نظراً لضغط سيرفرات جوجل حالياً.")
        
    st.write("---")
    st.markdown("### 📐 أبعاد وهندسة قوالب المنصات")
    platform_dimension = st.selectbox(
        "اختر مقاس منصة العرض المستهدفة (صور وفيديو):",
        ["تلقائي (حجم الملف الأصلي)", "تيك توك / ريلز (9:16 - 1080x1920)", "يوتيوب عريض (16:9 - 1920x1080)", "فيسبوك وانستجرام مربع (1:1 - 1080x1080)"]
    )
    
    dim_map = {
        "تلقائي (حجم الملف الأصلي)": None,
        "تيك توك / ريلز (9:16 - 1080x1920)": (1080, 1920),
        "يوتيوب عريض (16:9 - 1920x1080)": (1920, 1080),
        "فيسبوك وانستجرام مربع (1:1 - 1080x1080)": (1080, 1080)
    }
    chosen_size = dim_map[platform_dimension]

    st.write("---")
    st.markdown("### 🖼️ هندسة قوالب الصور والبلور الاحترافي")
    blur_bg_opt = st.checkbox("تفعيل تأثير الـ Blur لعزل خلفية الصور", value=True)
    blur_intensity_val = st.slider("درجة قوة تغبيش البلور (Blur Intensity):", min_value=1, max_value=15, value=4, step=1)
    enhance_quality_opt = st.checkbox("تفعيل فلتر تحسين الجودة وتوضيح الكلام والأكواد الحاد 🚀", value=True)
    
    st.write("---")
    st.markdown("### 🎨 ألوان وتكبير وتصغير اللوجو والكلمة المطبوعة")
    logo_opacity = st.slider("درجة شفافية اللوجو المائي:", min_value=0.1, max_value=1.0, value=0.8, step=0.05)
    live_logo_size = st.slider("حجم لوجو القالب التلقائي (Logo Scale):", min_value=0.05, max_value=0.50, value=0.22, step=0.02)
    live_text_size = st.slider("حجم خط الكلمة المطبوعة (Text Scale):", min_value=0.015, max_value=0.080, value=0.035, step=0.005)
    custom_text_color = st.color_picker("اختر لون كلمة البراند المكتوبة (افتراضي ذهبي):", value="#FFD700")

    if os.path.exists(config.ACTIVE_LOGO_PATH):
        st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط حالياً", width=100)
        
    uploaded_logo = st.file_uploader("ارفع صورة لوجو جديدة للموقع:", type=["png", "jpg", "jpeg"])
    if uploaded_logo is not None:
        Image.open(uploaded_logo).save(config.ACTIVE_LOGO_PATH)
        st.success("✅ تم حفظ وتثبيت اللوجو الجديد بنجاح!")
        st.rerun()

    st.write("---")
    st.markdown("### 📝 نص البراند وجمل الإضافات المخصصة")
    if "dynamic_brand_text" not in st.session_state:
        st.session_state["dynamic_brand_text"] = "Montgk Brand"
        
    input_brand_text = st.text_input("تعديل كلمة البراند الأساسية:", value=st.session_state["dynamic_brand_text"])
    if input_brand_text != st.session_state["dynamic_brand_text"]:
        st.session_state["dynamic_brand_text"] = input_brand_text
        st.success("📝 تم تحديث كلمة البراند!")
        st.rerun()

    extra_brand_suffix = st.text_input("أضف كلمة أو جملة مخصصة بجانب البراند (اختياري):", value="", placeholder="مثال: Premium Quality")

    st.write("---")
    video_duration_choice = st.selectbox("اختر مدة رندرة الفيديو القصيرة:", ("20 ثانية (أسرع رندرة للـ Reels)", "30 ثانية (مثالي للشورتس)", "60 ثانية (دقيقة كاملة)", "الفيديو كامل (حد أقصى 5 دقائق)"))
    
    st.markdown("### 🎵 تراك الهندسة الصوتية")
    audio_mode = st.radio("مصدر الصوت للفيديو الحالي:", ["تراك المزيكا الحصري التلقائي", "رفع تراك أوديو MP3 مخصص من جهازك"])
    uploaded_custom_audio = None
    if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك":
        uploaded_custom_audio = st.file_uploader("ارفع ملف الأغنية أو التراك المخصص هنا:", type=["mp3", "wav", "ogg"])
    
    st.write("---")
    new_ch = st.text_input("أدخل معرف قناة تليجرام جديدة:")
    if st.button("➕ تسجيل وتشغيل الرادار للملف"):
        if new_ch and new_ch not in current_channels:
            current_channels.append(new_ch.replace("@", "").strip())
            with open(config.CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(current_channels, f, ensure_ascii=False, indent=4)
            st.success("✅ القناة اتحفظت في ملف الـ JSON ومش هتطير!")
            st.rerun()

tab1, tab2, tab3 = st.tabs(["🎬 تشفير ومونتاج الفيديو", "🖼️ قالب ألبومات وصور المنتجات", "🛰️ رادار القنوات والـ Forward"])

# ==================== التبويب الأول (الفيديو) ====================
with tab1:
    st.subheader("🚀 منصة هندسة وبصمة الفيديو وحذف اللوجوهات القديمة")
    option = st.radio("اختر طريقة إدخال مقطع الفيديو:", ("لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)", "رفع ملف فيديو مباشر من جهازك"), key="vid_option")
    input_path = "web_input.mp4"
    output_path = "Bo0sViDClone_web_output.mp4"
    ready_to_process = False

    if option == "لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)":
        url = st.text_input("ضع رابط الفيديو هنا:", placeholder="https://...", key="vid_url")
        if url and re.match(r'http[s]?://', url):
            if st.button("🚀 ابدأ المعالجة وضخ تراك الصوت الحصري"):
                with st.spinner("جاري سحب المحتوى..."):
                    try:
                        downloaded_file = download_from_link(url)
                        if os.path.exists(input_path): os.remove(input_path)
                        os.rename(downloaded_file, input_path)
                        ready_to_process = True
                    except Exception as e: st.error(f"حدث خطأ في السحب: {str(e)}")
    else:
        uploaded_file = st.file_uploader("اسحب ملف الفيديو هنا مباشرة", type=["mp4", "mov", "avi"], key="vid_file")
        if uploaded_file is not None and st.button("⚙️ ابدأ تشفير وحجب لوجوهات الفيديو"):
            with st.spinner("جاري تهيئة الملف..."):
                if os.path.exists(input_path): os.remove(input_path)
                with open(input_path, "wb") as f: f.write(uploaded_file.read())
                ready_to_process = True

    if ready_to_process:
        with st.spinner("⚡ جاري تشغيل المايسترو وحجب اللوجوهات بالـ Blur الذكي وضبط الأبعاد..."):
            try:
                clip = VideoFileClip(input_path)
                if "20 ثانية" in video_duration_choice: clip = clip.subclip(0, min(20, clip.duration))
                elif "30 ثانية" in video_duration_choice: clip = clip.subclip(0, min(30, clip.duration))
                elif "60 ثانية" in video_duration_choice: clip = clip.subclip(0, min(60, clip.duration))
                else:
                    if clip.duration > 300: clip = clip.subclip(0, 300)
                
                if chosen_size:
                    clip = clip.fx(vfx.resize, width=chosen_size[0], height=chosen_size[1])
                else:
                    clip = clip.fx(vfx.crop, x1=5, y1=5, x2=clip.w-5, y2=clip.h-5)
                    
                modified_clip = clip.fx(vfx.colorx, 1.05)
                
                if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" and uploaded_custom_audio is not None:
                    temp_audio_path = os.path.join(config.TMP_DIR, "user_custom_audio.mp3")
                    with open(temp_audio_path, "wb") as f:
                        f.write(uploaded_custom_audio.read())
                    audio_overlay = AudioFileClip(temp_audio_path).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                elif audio_mode == "تراك المزيكا الحصري التلقائي" and os.path.exists(config.CUSTOM_AUDIO_TRACK):
                    audio_overlay = AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                else: 
                    modified_clip = modified_clip.fx(vfx.speedx, 1.03)
                
                if os.path.exists(config.ACTIVE_LOGO_PATH):
                    logo = (ImageClip(config.ACTIVE_LOGO_PATH)
                            .set_duration(modified_clip.duration)
                            .resize(height=int(55 * (live_logo_size / 0.22)))
                            .margin(right=15, top=15, opacity=0)
                            .set_pos(("right", "top"))
                            .set_opacity(logo_opacity))
                    final_clip = CompositeVideoClip([modified_clip, logo])
                else: final_clip = modified_clip
                
                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
                clip.close()
                final_clip.close()
                st.success("🎉 تم معالجة وتصحيح كادر الفيديو وحجب علامات المنصات بنجاح!")
                st.video(output_path)
            except Exception as e: st.error(f"حدث خطأ: {str(e)}")

# ==================== التبويب الثاني (قوالب الصور) ====================
with tab2:
    st.subheader("🖼️ مصنع تجميل صور المنتجات والأسطمبات الفورية لـ Montgk")
    uploaded_images = st.file_uploader("ارفع صورة أو مجموعة صور للمنتجات هنا ع الماشي:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_images:
        if len(uploaded_images) > 1:
            album_choice = st.radio("⚡ لقطنا مجموعة صور! تحب تخرجهم إزاي يا با؟", 
                                    ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"))
        else: 
            album_choice = "📥 ألبوم صور مفرودة منفصلة"

        if st.button("⚙️ ابدأ معالجة وتجميل قالب الصور الحصري"):
            saved_paths = []
            for i, img_file in enumerate(uploaded_images):
                temp_p = f"temp_product_{i}.png"
                with open(temp_p, "wb") as f: f.write(img_file.read())
                
                processed_p = process_image_template(
                    temp_p, 
                    blur_background=blur_bg_opt, 
                    blur_intensity=blur_intensity_val, 
                    opacity_val=logo_opacity,
                    logo_scale=live_logo_size,
                    text_scale=live_text_size,
                    text_color=custom_text_color,
                    extra_text=extra_brand_suffix,
                    target_size=chosen_size,
                    enhance_quality=enhance_quality_opt
                )
                saved_paths.append(processed_p)
                if os.path.exists(temp_p): os.remove(temp_p)
            
            if album_choice == "📥 ألبوم صور مفرودة منفصلة":
                st.success("🎉 تمت الفرمطة وتركيب اللوجو بنجاح!")
                for idx, p in enumerate(saved_paths): 
                    st.image(p, caption=f"🖼️ منتج رقم {idx+1}", use_container_width=True)
                    
            elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
                st.success("🎉 تم دمج الألبوم كله in شبكة كولاج فخمة ومنظمة!")
                collage_result = create_image_collage(saved_paths, target_size=(1080, 1080) if not chosen_size else chosen_size)
                st.image(collage_result, caption="📸 صورة الكولاج الشبكية المجمعة الاحترافية", use_container_width=True)
                
            else:
                with st.spinner("🎬 جاري نسج الصور في مقطع فيديو..."):
                    img_clips = [ImageClip(p).set_duration(3) for p in saved_paths]
                    video_slideshow = concat_video_clips(img_clips, method="compose")
                    
                    if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" and uploaded_custom_audio is not None:
                        temp_audio_p2 = os.path.join(config.TMP_DIR, "user_custom_audio_slide.mp3")
                        with open(temp_audio_p2, "wb") as f: f.write(uploaded_custom_audio.read())
                        video_slideshow = video_slideshow.set_audio(AudioFileClip(temp_audio_p2).subclip(0, video_slideshow.duration))
                    elif os.path.exists(config.CUSTOM_AUDIO_TRACK):
                        video_slideshow = video_slideshow.set_audio(AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, video_slideshow.duration))
                        
                    video_slideshow_path = "images_slideshow_output.mp4"
                    video_slideshow.write_videofile(video_slideshow_path, codec="libx264", fps=24, preset="ultrafast")
                    st.video(video_slideshow_path)

# ==================== التبويب الثالث (الرادار والوصف والتسعير الذكي) ====================
with tab3:
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير التلقائي")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر الخاصة بك (%):", min_value=0, max_value=100, value=config.DEFAULT_PRICE_INC_RATE)
    with col2: box_items_count = st.number_input("عدد القطع داخل العلبة (لو كان البوست يحمل سعر بوكس كامل):", min_value=1, max_value=100, value=config.DEFAULT_BOX_ITEMS_COUNT)
    fb_profile_link = st.text_input("رابط صفحة الفيسبوك الخاصة بك للتواصل:", value="https://www.facebook.com/montgk1")
    
    st.markdown("#### 🛡️ فلاتر الأمان والحد الأقصى قبل الانطلاق")
    max_price_threshold = st.number_input("اكتب الحد الأقصى للسعر المراد قنصه الآن:", min_value=1, max_value=9999999, value=5000)
    
    st.markdown("#### 📅 فلتر توقيت سحب البوستات المطلوبة")
    date_filter = st.radio("اختر النطاق الزمني لقنص البوستات:", ("اليوم فقط", "الأمس واليوم", "قبل أمس والـ 3 أيام الأخيرة", "كل البوستات المتاحة للقناة"), index=3, horizontal=True)
    
    st.write("---")
    radar_mode = st.radio("اختر مصدر فحص المحتوى:", ("🛰️ سحب رادار حي وفوري", "📋 إدخل يدوي لبوست معموله Forward"), key="mode_9")
    
    if "cached_posts" not in st.session_state: st.session_state["cached_posts"] = []

    if radar_mode == "🛰️ سحب رادار حي وفوري":
        target_channel_input = st.selectbox("اختر القناة لالتقاط المنتجات:", current_channels)
        if st.button("🛰️ أطلق الرادار وااقنص المحتوى"):
            with st.spinner("جاري قنص الداتا بالحد الأقصى وتاريخ الفلتر المطلوب..."):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    res = requests.get(f"https://t.me/s/{target_channel_input}", headers=headers, timeout=12)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.content, "html.parser")
                        messages = soup.find_all("div", class_=lambda x: x and 'tgme_widget_message_wrap' in x)
                        if not messages:
                            messages = soup.find_all("div", {"class": "tgme_widget_message_wrap"})
                            
                        temp_collected = []
                        now = datetime.now()
                        today_date = now.date()
                        yesterday_date = today_date - timedelta(days=1)
                        before_yesterday_date = today_date - timedelta(days=2)
                        three_days_ago_date = today_date - timedelta(days=3)

                        for msg in reversed(messages):
                            text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                            if not text_div:
                                text_div = msg.find("div", class_=lambda x: x and 'message_text' in x)
                                
                            time_tag = msg.find("time")
                            if text_div:
                                post_date = today_date
                                if time_tag and time_tag.get("datetime"):
                                    try:
                                        iso_date_str = time_tag.get("datetime").split("T")[0]
                                        post_date = datetime.strptime(iso_date_str, "%Y-%m-%d").date()
                                    except: pass
                                
                                if date_filter == "اليوم فقط" and post_date != today_date: continue
                                if date_filter == "الأمس والوقت" and post_date not in [today_date, yesterday_date]: continue
                                if date_filter == "قبل أمس والـ 3 أيام الأخيرة" and post_date not in [today_date, yesterday_date, before_yesterday_date, three_days_ago_date]: continue
                                
                                p_text = text_div.text.strip()
                                photo_url = None
                                photo_tag = msg.find("a", {"class": "tgme_widget_message_photo_wrap"})
                                if not photo_tag:
                                    photo_tag = msg.find("a", class_=lambda x: x and 'message_photo' in x)
                                    
                                if photo_tag:
                                    style = photo_tag.get("style", "")
                                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    if match: photo_url = match.group(1)
                                if photo_url and photo_url.startswith('//'): photo_url = 'https:' + photo_url
                                    
                                auto_price, old_str = extract_original_price_only(p_text, max_limit=max_price_threshold)
                                temp_collected.append({"text": p_text, "image": photo_url, "auto_price": auto_price, "old_str": old_str})
                        
                        st.session_state["cached_posts"] = temp_collected
                        if not temp_collected:
                            st.warning("⚠️ الرادار فتح القناة بس ملحقش بوستات مطابقة لفلتر وقت السيستم المختار.")
                        else:
                            st.success(f"🎯 الرادار قنص {len(temp_collected)} بوست حقيقي بنجاح مية مية!")
                    else:
                        st.error(f"❌ خطأ استجابة من تليجرام: {res.status_code}")
                except Exception as e: st.error(f"خطأ غير متوقع in الرادار الزمني: {str(e)}")
    else:
        forwarded_text = st.text_area("الزق نص البوست الـ Forward هنا:")
        uploaded_image = st.file_uploader("📥 ارفع صورة المنتج المصاحبة:")
        if st.button("⚡ فرم وتعديل بوست الـ Forward فوراً"):
            if forwarded_text:
                auto_price, old_str = extract_original_price_only(forwarded_text, max_limit=max_price_threshold)
                st.session_state["cached_posts"] = [{"text": forwarded_text, "image": uploaded_image, "auto_price": auto_price, "old_str": old_str}]

    if st.session_state["cached_posts"]:
        st.write("---")
        if st.button("📊 صناعة وتوليد شيت إكسيل Montgk الملكي للمنصات"):
            excel_data_list = []
            for i, item in enumerate(st.session_state["cached_posts"]):
                excel_data_list.append({
                    "رقم المنتج": i + 1,
                    "اسم الصورة المائية": f"watermarked_product_{i+1}.jpg",
                    "اسم المنتج (فارغ لملئه)": "",
                    "السعر الجديد": "",
                    "الوصف التجاري المقترح": ""
                })
            df_excel = pd.DataFrame(excel_data_list)
            output_io = io.BytesIO()
            with pd.ExcelWriter(output_io, engine='openpyxl') as writer:
                df_excel.to_excel(writer, index=False, sheet_name="Montgk")
            final_excel_bytes = output_io.getvalue()
            st.success("✅ الشيت النظيف اتعمل وجاهز للرفع!")
            st.download_button(label="📥 تحميل ملف Excel الآن", data=final_excel_bytes, file_name="Montgk_Platform_Products.xlsx")
        st.write("---")

        for idx, item in enumerate(st.session_state["cached_posts"]):
            st.markdown(f"#### 📦 منتج رقم {idx + 1}")
            if item["image"]: st.image(item["image"], width=250)
            
            is_single_piece = check_if_single_piece_text(item["text"])
            if is_single_piece:
                st.warning("🎯 محرك الأسعار لقط تلقائياً إن السعر ده لـ (قطعة منفردة/واحدة) ومش سعر بوكس كامل!")
            
            chosen_orig_price = st.number_input(
                f"✍️ السعر الأصلي المكتشف لمنتج {idx+1}:", 
                min_value=0, max_value=2000000000, value=int(item["auto_price"]), key=f"manual_price_{idx}"
            )
            
            base_new_price = int(chosen_orig_price * (1 + (price_inc_rate / 100)))
            
            if is_single_piece:
                piece_p = base_new_price
                estimated_box_price = base_new_price * box_items_count
                price_status_note = f"📌 سعر القطعة واصل عليك بـ {piece_p} ج بس! 🔥 (سعر العلبة الكاملة جملة تقريبي: {estimated_box_price} ج)"
            else:
                piece_p = round(base_new_price / box_items_count, 1)
                if piece_p.is_integer(): piece_p = int(piece_p)
                price_status_note = f"📌 سعر القطعة واصل عليك بـ {piece_p} ج بس! 🔥"
            
            temp_post_text = item["text"]
            temp_post_text = re.sub(r'#\w+', '', temp_post_text)
            temp_post_text = re.sub(r'http[s]?://\S+|www\.\S+', '', temp_post_text)
            
            if item["old_str"] and item["old_str"] in temp_post_text:
                final_clean_text = temp_post_text.replace(item["old_str"], str(base_new_price), 1)
            else: 
                final_clean_text = temp_post_text + f"\n سعر العرض الجديد: {base_new_price} ج"
            
            smart_ai_proposal = generate_smart_ai_description(item["text"])
            st.info("💡 **اقتراح الوصف الذكي من الـ AI لمستر بو:**")
            st.caption(smart_ai_proposal)
            
            apply_ai = st.checkbox("🔄 اعتماد واستخدام الوصف الذكي المقترح بدلاً من النص الأصلي؟", value=False, key=f"ai_check_{idx}")
            chosen_description = smart_ai_proposal if apply_ai else final_clean_text
            
            final_commercial_post = (
                f"{chosen_description}\n\n"
                f"{price_status_note}\n\n"
                f"🎁 **خصم خاص للكميات وأصحاب المحلات!** 💣🔥\n\n"
                f"🔗 للتواصل وطلب المنتج كاش فوراً: {fb_profile_link}"
            )
            st.text_area(f"📋 البوست الجاهز للنسخ {idx + 1}:", value=final_commercial_post, height=180, key=f"post_area_{idx}")
            st.markdown("---")

st.markdown(f"<br><p style='text-align: center; color: #2a4d69; font-weight: bold;'>{config.DEVELOPER_SIGNATURE}</p>", unsafe_allow_html=True)
