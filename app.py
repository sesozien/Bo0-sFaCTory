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
from rembg import remove  # الميزة الذكية رقم 3

# التعديل النهائي المعتمد لنسخة MoviePy 2.0+
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips as concat_video_clips

import moviepy.video.fx as vfx
import yt_dlp
import io
import pandas as pd

import arabic_reshaper
from bidi.algorithm import get_display

import config

st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="centered")

current_channels = config.load_and_sync_channels()

if not os.path.exists(config.DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)
if not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)

# --- نظام حفظ واسترجاع الإعدادات الافتراضية ---
DEFAULT_SETTINGS = {
    "l_pos": "فوق يمين (Top-Right)",
    "l_ox": 0, "l_oy": 0,
    "logo_opacity": 0.8,
    "logo_fit_auto": True,
    "logo_custom_w": 200, "logo_custom_h": 200,
    "b_pos": "تحت شمال (Bottom-Left)",
    "b_ox": 0, "b_oy": 0,
    "b_sc": 0.035, "b_cl": "#FFD700",
    "e_pos": "تحت يمين (Bottom-Right)",
    "e_ox": 0, "e_oy": 0,
    "e_sc": 0.025, "e_cl": "#FFFFFF",
    "slide_dur": 3,
    "blur_bg": True,
    "blur_val": 15,
    "remove_bg": False,  # ميزة التفريغ الذكي
    "enhance_opt": True,
    "sharp_val": 2.0,
    "dynamic_brand_text": "Montgk Brand"
}

for k, v in DEFAULT_SETTINGS.items():
    if k not in st.session_state:
        st.session_state[k] = v

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

def get_arabic_font(font_size=24):
    for folder_name in ["Cairo", "cairo"]:
        if os.path.exists(folder_name) and os.path.isdir(folder_name):
            files = [f for f in os.listdir(folder_name) if f.lower().endswith('.ttf')]
            if files:
                font_path = os.path.join(folder_name, files[0])
                try: return ImageFont.truetype(font_path, font_size)
                except: pass
                
    font_dir = os.path.join(os.path.expanduser("~"), ".fonts")
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, "Cairo-Bold.ttf")
    
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"
            r = requests.get(url, timeout=15)
            with open(font_path, "wb") as f: f.write(r.content)
        except: return None
            
    try: return ImageFont.truetype(font_path, font_size)
    except: return None

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def calculate_element_position(img_w, img_h, elem_w, elem_h, pos_mode, off_x, off_y):
    x, y = 15, 15
    if pos_mode == "فوق يمين (Top-Right)":
        x = img_w - elem_w - 15 - off_x
        y = 15 + off_y
    elif pos_mode == "فوق شمال (Top-Left)":
        x = 15 + off_x
        y = 15 + off_y
    elif pos_mode == "في المنتصف تماماً (Center)":
        x = (img_w - elem_w) // 2 + off_x
        y = (img_h - elem_h) // 2 + off_y
    elif pos_mode == "تحت يمين (Bottom-Right)":
        x = img_w - elem_w - 15 - off_x
        y = img_h - elem_h - 15 - off_y
    elif pos_mode == "تحت شمال (Bottom-Left)":
        x = 15 + off_x
        y = img_h - elem_h - 15 - off_y
        
    if x < 0: x = 0
    if y < 0: y = 0
    if x + elem_w > img_w: x = img_w - elem_w
    if y + elem_h > img_h: y = img_h - elem_h
    
    return int(x), int(y)

def draw_single_custom_text(img, text, font, fill_color, pos_mode, off_x, off_y):
    if not text.strip(): return
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox(bidi_text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    else:
        text_w, text_h = draw.textsize(bidi_text, font=font)
        
    pad_x, pad_y = 20, 12
    box_w = text_w + (pad_x * 2)
    box_h = text_h + (pad_y * 2)
    
    bx, by = calculate_element_position(w, h, box_w, box_h, pos_mode, off_x, off_y)
    
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=10, fill=(0, 0, 0, 140))
    img.alpha_composite(overlay)
    
    draw = ImageDraw.Draw(img)
    text_position = (bx + pad_x, by + pad_y - 2)
    
    draw.text((text_position[0] + 2, text_position[1] + 2), bidi_text, fill=(0, 0, 0, 220), font=font)
    draw.text(text_position, bidi_text, fill=fill_color, font=font)

def generate_smart_ai_description(raw_text):
    clean = re.sub(r'http[s]?://\S+|www\.\S+', '', raw_text)
    clean = re.sub(r'#\w+', '', clean)
    clean = re.sub(r'01[0125]\d{8}', '', clean)
    clean = re.sub(r'\d+\s*(?:شارع|طريق|ميدان|دور|شقة|مكرر)', '', clean)
    words = clean.split()
    useful_words = [w for w in words if not w.isdigit()]
    base_description = " ".join(useful_words[:25])
    
    return (
        f"✨ **اللقطة اللي مستنيها وصلت!** ✨\n"
        f"🔥 {base_description} 🔥\n"
        f"شغل مستورد فاخر وخامات توب التوب، جبناهالك لحد عندك بأعلى جودة وأقل سعر في مصر عشان تكتسح السوق وتنافس بثقة! 😉👑"
    )

def enhance_image_quality(pil_img, sharpness_factor=2.0):
    sharpener = ImageEnhance.Sharpness(pil_img)
    pil_img = sharpener.enhance(sharpness_factor) 
    contrast = ImageEnhance.Contrast(pil_img)
    pil_img = contrast.enhance(1.15)
    return pil_img

def process_image_template(image_path, blur_background=True, blur_intensity=12, opacity_val=0.8, 
                           fit_auto_logo=True, logo_custom_w=200, logo_custom_h=200,
                           brand_text_scale=0.035, brand_color="#FFD700", brand_pos="تحت شمال (Bottom-Left)", brand_off_x=0, brand_off_y=0,
                           extra_text="", extra_text_scale=0.025, extra_color="#FFFFFF", extra_pos="تحت يمين (Bottom-Right)", extra_off_x=0, extra_off_y=0,
                           target_size=None, enhance_quality=True, sharpness_val=2.0, logo_pos_mode="فوق يمين (Top-Right)", logo_off_x=0, logo_off_y=0,
                           remove_bg_ai=False):
    
    img = Image.open(image_path).convert("RGBA")
    
    if enhance_quality:
        img = enhance_image_quality(img, sharpness_val)
        
    # تفريغ الخلفية بالذكاء الاصطناعي لو الخيار متفعل
    if remove_bg_ai:
        try:
            fg_no_bg = remove(img)
        except Exception:
            fg_no_bg = img
    else:
        fg_no_bg = img

    if target_size:
        tw, th = target_size
        if blur_background:
            bg = img.copy().resize((tw, th), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (tw, th), (0, 0, 0, 50))
            bg = Image.alpha_composite(bg, dimmer)
        else:
            bg = Image.new("RGBA", target_size, (14, 17, 23, 255))
            
        fg = fg_no_bg.copy()
        fg.thumbnail((tw, th), Image.Resampling.LANCZOS)
        offset = ((tw - fg.size[0]) // 2, (th - fg.size[1]) // 2)
        bg.paste(fg, offset, fg)
        img = bg
    else:
        if blur_background:
            w, h = img.size
            bg = img.copy().filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (w, h), (0, 0, 0, 50))
            bg = Image.alpha_composite(bg, dimmer)
            
            fg = fg_no_bg.copy()
            fg.thumbnail((int(w * 0.9), int(h * 0.9)), Image.Resampling.LANCZOS)
            offset = ((w - fg.size[0]) // 2, (h - fg.size[1]) // 2)
            bg.paste(fg, offset, fg)
            img = bg

    w, h = img.size

    # 1. طباعة اللوجو
    if os.path.exists(config.ACTIVE_LOGO_PATH):
        logo = Image.open(config.ACTIVE_LOGO_PATH).convert("RGBA")
        
        if fit_auto_logo:
            logo.thumbnail((int(w * 0.22), int(h * 0.12)), Image.Resampling.LANCZOS)
        else:
            logo = logo.resize((logo_custom_w, logo_custom_h), Image.Resampling.LANCZOS)
            
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * opacity_val))
        logo_transparent = Image.merge("RGBA", (r, g, b, a))
        
        lx, ly = calculate_element_position(w, h, logo.size[0], logo.size[1], logo_pos_mode, logo_off_x, logo_off_y)
        img.paste(logo_transparent, (lx, ly), logo_transparent)

    # 2. طباعة اسم البراند
    base_brand_text = st.session_state.get("dynamic_brand_text", "Montgk Brand")
    calc_b_size = max(14, int(h * brand_text_scale))
    b_font = get_arabic_font(calc_b_size)
    if b_font:
        draw_single_custom_text(img, base_brand_text, b_font, hex_to_rgb(brand_color) + (255,), brand_pos, brand_off_x, brand_off_y)

    # 3. طباعة الجملة الإضافية
    if extra_text.strip():
        calc_e_size = max(12, int(h * extra_text_scale))
        e_font = get_arabic_font(calc_e_size)
        if e_font:
            draw_single_custom_text(img, extra_text, e_font, hex_to_rgb(extra_color) + (255,), extra_pos, extra_off_x, extra_off_y)

    out_img_path = os.path.join(config.TMP_DIR, f"templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=95)
    return out_img_path

def create_image_collage(image_paths, target_size=(1080, 1080)):
    num_images = len(image_paths)
    collage_img = Image.new('RGB', target_size, color=(14, 17, 23))
    
    if num_images == 2: cols, rows = 2, 1
    elif num_images <= 4: cols, rows = 2, 2
    elif num_images <= 6: cols, rows = 3, 2
    else: cols, rows = 3, 3

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
    single_piece_keywords = ["سعر القطعه", "سعر القطعة", "سعر الحته", "سعر الحتة", "السعر للقطعه", "الواحدة", "سعر الواحدة"]
    for kw in single_piece_keywords:
        if kw in text: return True
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
        if val < 50000: return val, num_str
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

# ==================== 🛠️ لوحة التحكم الجانبية ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛰️ ترسانة السيطرة والتوقيت</h2>", unsafe_allow_html=True)
    
    c_save, c_reset = st.columns(2)
    with c_save:
        if st.button("💾 حفظ الإعدادات"):
            st.success("✅ تم حفظ التفضيلات!")
    with c_reset:
        if st.button("🔄 إرجاع للافتراضي"):
            for k, v in DEFAULT_SETTINGS.items(): st.session_state[k] = v
            st.rerun()

    st.write("---")
    st.markdown("### 📐 أبعاد وهندسة قوالب المنصات")
    platform_dimension = st.selectbox(
        "اختر مقاس منصة العرض المستهدفة:",
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
    st.markdown("### 🎯 1. التحكم في اللوجو المائي")
    logo_position_choice = st.selectbox("مكان اللوجو:", ["فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)", "تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)"], key="l_pos")
    logo_offset_x = st.slider("زق اللوجو أفقي (X):", -300, 300, key="l_ox")
    logo_offset_y = st.slider("زق اللوجو رأسي (Y):", -300, 300, key="l_oy")
    logo_opacity = st.slider("شفافية اللوجو:", 0.1, 1.0, key="logo_opacity")
    
    fit_auto_logo = st.checkbox("التكيف التلقائي تناسباً مع الصورة (Auto Fit)", key="logo_fit_auto")
    if not fit_auto_logo:
        logo_custom_w = st.slider("عرض اللوجو (px):", 20, 800, key="logo_custom_w")
        logo_custom_h = st.slider("ارتفاع اللوجو (px):", 20, 800, key="logo_custom_h")
    else:
        logo_custom_w, logo_custom_h = 200, 200

    st.write("---")
    st.markdown("### 🏷️ 2. التحكم في اسم البراند")
    input_brand_text = st.text_input("نص البراند:", key="dynamic_brand_text")
    brand_position_choice = st.selectbox("مكان اسم البراند:", ["تحت شمال (Bottom-Left)", "تحت يمين (Bottom-Right)", "فوق شمال (Top-Left)", "فوق يمين (Top-Right)", "في المنتصف تماماً (Center)"], key="b_pos")
    brand_offset_x = st.slider("زق البراند أفقي (X):", -300, 300, key="b_ox")
    brand_offset_y = st.slider("زق البراند رأسي (Y):", -300, 300, key="b_oy")
    brand_text_scale = st.slider("حجم خط البراند:", 0.015, 0.080, key="b_sc")
    brand_color = st.color_picker("لون خط البراند:", key="b_cl")

    st.write("---")
    st.markdown("### ✍️ 3. الجملة الإضافية المخصصة")
    extra_brand_suffix = st.text_input("الجملة الإضافية:", value="", placeholder="مثال: Premium Quality")
    extra_position_choice = st.selectbox("مكان الجملة الإضافية:", ["تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)", "فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)"], key="e_pos")
    extra_offset_x = st.slider("زق الجملة أفقي (X):", -300, 300, key="e_ox")
    extra_offset_y = st.slider("زق الجملة رأسي (Y):", -300, 300, key="e_oy")
    extra_text_scale = st.slider("حجم خط الجملة:", 0.010, 0.060, key="e_sc")
    extra_color = st.color_picker("لون خط الجملة:", key="e_cl")

    st.write("---")
    st.markdown("### ⏱️ 4. مدة عرض كل صورة بالفيديو")
    image_duration_per_slide = st.slider("مدة عرض الصورة المفرودة (بالثواني):", min_value=1, max_value=10, key="slide_dur")

    st.write("---")
    st.markdown("### 🖼️ 5. فلاتر الصور والذكاء الاصطناعي")
    remove_bg_opt = st.checkbox("تفريغ خلفية المنتج بالذكاء الاصطناعي (AI Background Remover) 🤖", key="remove_bg")
    blur_bg_opt = st.checkbox("تفعيل خلفية Blur من نفس الصورة", key="blur_bg")
    blur_intensity_val = st.slider("قوة تغبيش الخلفية (Blur Radius):", 1, 30, key="blur_val")
    enhance_quality_opt = st.checkbox("تفعيل فلتر الجودة والحدة 🚀", key="enhance_opt")
    sharpness_slider_val = st.slider("مستوى حدة التفاصيل (Sharpness):", 0.0, 5.0, key="sharp_val")

    if os.path.exists(config.ACTIVE_LOGO_PATH):
        st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط", width=100)
    uploaded_logo = st.file_uploader("تغيير اللوجو:", type=["png", "jpg", "jpeg"])
    if uploaded_logo is not None:
        Image.open(uploaded_logo).save(config.ACTIVE_LOGO_PATH)
        st.success("✅ تم التحديث!")
        st.rerun()

    st.write("---")
    video_duration_choice = st.selectbox("مدة الفيديو المرفوع/المسحوب:", ("20 ثانية (أسرع رندرة للـ Reels)", "30 ثانية (مثالي للشورتس)", "60 ثانية (دقيقة كاملة)", "الفيديو كامل (حد أقصى 5 دقائق)"))
    audio_mode = st.radio("مصدر الصوت:", ["تراك المزيكا الحصري التلقائي", "رفع تراك أوديو MP3 مخصص من جهازك"])
    uploaded_custom_audio = None
    if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك":
        uploaded_custom_audio = st.file_uploader("ارفع الأوديو:", type=["mp3", "wav", "ogg"])
    
    st.write("---")
    new_ch = st.text_input("إضافة قناة تليجرام:")
    if st.button("➕ حفظ القناة"):
        if new_ch and new_ch not in current_channels:
            current_channels.append(new_ch.replace("@", "").strip())
            with open(config.CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(current_channels, f, ensure_ascii=False, indent=4)
            st.success("✅ اتنقلت للمفضلة!")
            st.rerun()

tab1, tab2, tab3 = st.tabs(["🎬 تشفير ومونتاج الفيديو", "🖼️ قالب ألبومات وصور المنتجات", "🛰️ رادار القنوات والـ Forward"])

# ==================== التبويب الأول (الفيديو) ====================
with tab1:
    st.subheader("🚀 منصة هندسة وبصمة الفيديو وحذف اللوجوهات القديمة")
    option = st.radio("إدخال الفيديو:", ("لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)", "رفع ملف فيديو مباشر من جهازك"), key="vid_option")
    input_path = "web_input.mp4"
    output_path = "Bo0sViDClone_web_output.mp4"
    ready_to_process = False

    if option == "لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)":
        url = st.text_input("ضع الرابط:", placeholder="https://...", key="vid_url")
        if url and re.match(r'http[s]?://', url):
            if st.button("🚀 ابدأ معالجة الفيديو"):
                with st.spinner("جاري سحب المحتوى..."):
                    try:
                        downloaded_file = download_from_link(url)
                        if os.path.exists(input_path): os.remove(input_path)
                        os.rename(downloaded_file, input_path)
                        ready_to_process = True
                    except Exception as e: st.error(f"خطأ في السحب: {str(e)}")
    else:
        uploaded_file = st.file_uploader("اسحب الفيديو هنا", type=["mp4", "mov", "avi"], key="vid_file")
        if uploaded_file is not None and st.button("⚙️ ابدأ معالجة الفيديو"):
            with st.spinner("جاري تهيئة الملف..."):
                if os.path.exists(input_path): os.remove(input_path)
                with open(input_path, "wb") as f: f.write(uploaded_file.read())
                ready_to_process = True

    if ready_to_process:
        with st.spinner("⚡ جاري الرندرة وتطبيق الإعدادات..."):
            try:
                clip = VideoFileClip(input_path)
                if "20 ثانية" in video_duration_choice: clip = clip.subclip(0, min(20, clip.duration))
                elif "30 ثانية" in video_duration_choice: clip = clip.subclip(0, min(30, clip.duration))
                elif "60 ثانية" in video_duration_choice: clip = clip.subclip(0, min(60, clip.duration))
                else:
                    if clip.duration > 300: clip = clip.subclip(0, 300)
                
                if chosen_size: clip = clip.fx(vfx.resize, width=chosen_size[0], height=chosen_size[1])
                else: clip = clip.fx(vfx.crop, x1=5, y1=5, x2=clip.w-5, y2=clip.h-5)
                    
                modified_clip = clip.fx(vfx.colorx, 1.05)
                
                if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" and uploaded_custom_audio is not None:
                    temp_audio_path = os.path.join(config.TMP_DIR, "user_custom_audio.mp3")
                    with open(temp_audio_path, "wb") as f: f.write(uploaded_custom_audio.read())
                    audio_overlay = AudioFileClip(temp_audio_path).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                elif audio_mode == "تراك المزيكا الحصري التلقائي" and os.path.exists(config.CUSTOM_AUDIO_TRACK):
                    audio_overlay = AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                else: modified_clip = modified_clip.fx(vfx.speedx, 1.03)
                
                if os.path.exists(config.ACTIVE_LOGO_PATH):
                    v_logo_h = logo_custom_h if not fit_auto_logo else int(modified_clip.h * 0.12)
                    v_logo_w = logo_custom_w if not fit_auto_logo else int(modified_clip.w * 0.22)
                    
                    vx, vy = calculate_element_position(modified_clip.w, modified_clip.h, v_logo_w, v_logo_h, logo_position_choice, logo_offset_x, logo_offset_y)
                    
                    logo = (ImageClip(config.ACTIVE_LOGO_PATH)
                            .set_duration(modified_clip.duration)
                            .resize(newsize=(v_logo_w, v_logo_h))
                            .set_pos((vx, vy))
                            .set_opacity(logo_opacity))
                    final_clip = CompositeVideoClip([modified_clip, logo])
                else: final_clip = modified_clip
                
                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
                clip.close()
                final_clip.close()
                st.success("🎉 تم المونتاج بنجاح!")
                st.video(output_path)
            except Exception as e: st.error(f"حدث خطأ: {str(e)}")

# ==================== التبويب الثاني (قوالب الصور) ====================
with tab2:
    st.subheader("🖼️ مصنع تجميل صور المنتجات والأسطمبات الفورية لـ Montgk")
    uploaded_images = st.file_uploader("ارفع الصور هنا:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_images:
        if len(uploaded_images) > 1:
            album_choice = st.radio("اختر نمط التصدير:", ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"))
        else: album_choice = "📥 ألبوم صور مفرودة منفصلة"

        if st.button("⚙️ ابدأ معالجة الصور"):
            saved_paths = []
            for i, img_file in enumerate(uploaded_images):
                temp_p = f"temp_product_{i}.png"
                with open(temp_p, "wb") as f: f.write(img_file.read())
                
                processed_p = process_image_template(
                    temp_p, 
                    blur_background=blur_bg_opt, 
                    blur_intensity=blur_intensity_val, 
                    opacity_val=logo_opacity,
                    fit_auto_logo=fit_auto_logo,
                    logo_custom_w=logo_custom_w,
                    logo_custom_h=logo_custom_h,
                    
                    brand_text_scale=brand_text_scale,
                    brand_color=brand_color,
                    brand_pos=brand_position_choice,
                    brand_off_x=brand_offset_x,
                    brand_off_y=brand_offset_y,
                    
                    extra_text=extra_brand_suffix,
                    extra_text_scale=extra_text_scale,
                    extra_color=extra_color,
                    extra_pos=extra_position_choice,
                    extra_off_x=extra_offset_x,
                    extra_off_y=extra_offset_y,
                    
                    target_size=chosen_size,
                    enhance_quality=enhance_quality_opt,
                    sharpness_val=sharpness_slider_val,
                    logo_pos_mode=logo_position_choice,
                    logo_off_x=logo_offset_x,
                    logo_off_y=logo_offset_y,
                    remove_bg_ai=remove_bg_opt
                )
                saved_paths.append(processed_p)
                if os.path.exists(temp_p): os.remove(temp_p)
            
            if album_choice == "📥 ألبوم صور مفرودة منفصلة":
                st.success("🎉 تمت المعالجة وتفرغت الصور وخلفية الـ Blur جاهزة!")
                for idx, p in enumerate(saved_paths): st.image(p, caption=f"🖼️ منتج رقم {idx+1}", use_container_width=True)
            elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
                st.success("🎉 تم دمج الصور في كولاج شبكي!")
                collage_result = create_image_collage(saved_paths, target_size=(1080, 1080) if not chosen_size else chosen_size)
                st.image(collage_result, caption="📸 صورة الكولاج المجمعة", use_container_width=True)
            else:
                with st.spinner(f"🎬 جاري رندرة السلايد شو (زمن كل صورة: {image_duration_per_slide} ثواني)..."):
                    img_clips = [ImageClip(p).set_duration(image_duration_per_slide) for p in saved_paths]
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

# ==================== التبويب الثالث (الرادار والوصف والتسعير) ====================
with tab3:
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير التلقائي")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر (%):", min_value=0, max_value=100, value=config.DEFAULT_PRICE_INC_RATE)
    with col2: box_items_count = st.number_input("عدد القطع بالعلبة:", min_value=1, max_value=100, value=config.DEFAULT_BOX_ITEMS_COUNT)
    fb_profile_link = st.text_input("رابط صفحتك للتواصل:", value="https://www.facebook.com/montgk1")
    
    max_price_threshold = st.number_input("الحد الأقصى للسعر:", min_value=1, max_value=9999999, value=5000)
    date_filter = st.radio("النطاق الزمني:", ("اليوم فقط", "الأمس واليوم", "قبل أمس والـ 3 أيام الأخيرة", "كل البوستات المتاحة للقناة"), index=3, horizontal=True)
    
    st.write("---")
    radar_mode = st.radio("مصدر المحتوى:", ("🛰️ سحب رادار حي وفوري", "📋 إدخل يدوي لبوست معموله Forward"), key="mode_9")
    
    if "cached_posts" not in st.session_state: st.session_state["cached_posts"] = []

    if radar_mode == "🛰️ سحب رادار حي وفوري":
        target_channel_input = st.selectbox("اختر القناة:", current_channels)
        if st.button("🛰️ قنص المحتوى"):
            with st.spinner("جاري السحب..."):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    res = requests.get(f"https://t.me/s/{target_channel_input}", headers=headers, timeout=12)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.content, "html.parser")
                        messages = soup.find_all("div", class_=lambda x: x and 'tgme_widget_message_wrap' in x)
                        if not messages: messages = soup.find_all("div", {"class": "tgme_widget_message_wrap"})
                            
                        temp_collected = []
                        now = datetime.now()
                        today_date = now.date()
                        yesterday_date = today_date - timedelta(days=1)
                        before_yesterday_date = today_date - timedelta(days=2)
                        three_days_ago_date = today_date - timedelta(days=3)

                        for msg in reversed(messages):
                            text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                            if not text_div: text_div = msg.find("div", class_=lambda x: x and 'message_text' in x)
                            time_tag = msg.find("time")
                            if text_div:
                                post_date = today_date
                                if time_tag and time_tag.get("datetime"):
                                    try:
                                        iso_date_str = time_tag.get("datetime").split("T")[0]
                                        post_date = datetime.strptime(iso_date_str, "%Y-%m-%d").date()
                                    except: pass
                                
                                if date_filter == "اليوم فقط" and post_date != today_date: continue
                                if date_filter == "الأمس واليوم" and post_date not in [today_date, yesterday_date]: continue
                                if date_filter == "قبل أمس والـ 3 أيام الأخيرة" and post_date not in [today_date, yesterday_date, before_yesterday_date, three_days_ago_date]: continue
                                
                                p_text = text_div.text.strip()
                                photo_url = None
                                photo_tag = msg.find("a", {"class": "tgme_widget_message_photo_wrap"})
                                if not photo_tag: photo_tag = msg.find("a", class_=lambda x: x and 'message_photo' in x)
                                    
                                if photo_tag:
                                    style = photo_tag.get("style", "")
                                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    if match: photo_url = match.group(1)
                                if photo_url and photo_url.startswith('//'): photo_url = 'https:' + photo_url
                                    
                                auto_price, old_str = extract_original_price_only(p_text, max_limit=max_price_threshold)
                                temp_collected.append({"text": p_text, "image": photo_url, "auto_price": auto_price, "old_str": old_str})
                        
                        st.session_state["cached_posts"] = temp_collected
                        if not temp_collected: st.warning("⚠️ لا توجد بوستات مطابقة.")
                        else: st.success(f"🎯 تم قنص {len(temp_collected)} بوست!")
                    else: st.error(f"❌ خطأ: {res.status_code}")
                except Exception as e: st.error(f"خطأ: {str(e)}")
    else:
        forwarded_text = st.text_area("نص البوست:")
        uploaded_image = st.file_uploader("الصورة:")
        if st.button("⚡ تعديل فوراً"):
            if forwarded_text:
                auto_price, old_str = extract_original_price_only(forwarded_text, max_limit=max_price_threshold)
                st.session_state["cached_posts"] = [{"text": forwarded_text, "image": uploaded_image, "auto_price": auto_price, "old_str": old_str}]

    if st.session_state["cached_posts"]:
        st.write("---")
        if st.button("📊 توليد شيت إكسيل Montgk"):
            excel_data_list = []
            for i, item in enumerate(st.session_state["cached_posts"]):
                excel_data_list.append({
                    "رقم المنتج": i + 1,
                    "اسم الصورة المائية": f"watermarked_product_{i+1}.jpg",
                    "اسم المنتج": "",
                    "السعر الجديد": "",
                    "الوصف المقترح": ""
                })
            df_excel = pd.DataFrame(excel_data_list)
            output_io = io.BytesIO()
            with pd.ExcelWriter(output_io, engine='openpyxl') as writer: df_excel.to_excel(writer, index=False, sheet_name="Montgk")
            st.success("✅ الشيت جاهز!")
            st.download_button(label="📥 تحميل Excel", data=output_io.getvalue(), file_name="Montgk_Platform_Products.xlsx")
        st.write("---")

        for idx, item in enumerate(st.session_state["cached_posts"]):
            st.markdown(f"#### 📦 منتج رقم {idx + 1}")
            if item["image"]: st.image(item["image"], width=250)
            
            is_single_piece = check_if_single_piece_text(item["text"])
            if is_single_piece: st.warning("🎯 سعر قطعة منفردة!")
            
            chosen_orig_price = st.number_input(
                f"✍️ السعر الأصلي {idx+1}:", 
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
            
            if item["old_str"] and item["old_str"] in temp_post_text: final_clean_text = temp_post_text.replace(item["old_str"], str(base_new_price), 1)
            else: final_clean_text = temp_post_text + f"\n سعر العرض الجديد: {base_new_price} ج"
            
            smart_ai_proposal = generate_smart_ai_description(item["text"])
            st.info("💡 **الوصف الذكي:**")
            st.caption(smart_ai_proposal)
            
            apply_ai = st.checkbox("🔄 اعتماد الوصف الذكي؟", value=False, key=f"ai_check_{idx}")
            chosen_description = smart_ai_proposal if apply_ai else final_clean_text
            
            final_commercial_post = (
                f"{chosen_description}\n\n"
                f"{price_status_note}\n\n"
                f"🎁 **خصم خاص للكميات وأصحاب المحلات!** 💣🔥\n\n"
                f"🔗 للتواصل وطلب المنتج كاش فوراً: {fb_profile_link}"
            )
            st.text_area(f"📋 البوست الجاهز {idx + 1}:", value=final_commercial_post, height=180, key=f"post_area_{idx}")
            st.markdown("---")

st.markdown(f"<br><p style='text-align: center; color: #2a4d69; font-weight: bold;'>{config.DEVELOPER_SIGNATURE}</p>", unsafe_allow_html=True)
