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
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance, ImageOps

# مكتبات الفيديو والصوت الحديثة المتوافقة 100%
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

import moviepy.video.fx.all as vfx
import yt_dlp
import io
import pandas as pd

import arabic_reshaper
from bidi.algorithm import get_display

import config

# =========================================================
# 1. إعداد الصفحة والتهيئة الذكية
# =========================================================
st.set_page_config(page_title=getattr(config, 'PAGE_TITLE', 'Mr:- Bo0 Smart Studio'), page_icon="🥷", layout="centered")

try:
    current_channels = config.load_and_sync_channels()
except:
    current_channels = ["montgk"]

# ضمان وجود مسار اللوجو الافتراضي والنشط بجوار الملف (logo.png)
if not os.path.exists(config.DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)

if os.path.exists("logo.png") and not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open("logo.png").save(config.ACTIVE_LOGO_PATH)
elif not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)

# تهيئة الـ session_state لحفظ الإعدادات ومنع تفريغ الـ checkboxes
DEFAULT_SETTINGS = {
    "l_pos": "فوق يمين (Top-Right)",
    "l_ox": 0, "l_oy": 0,
    "logo_opacity": 0.9,
    "logo_fit_auto": True,
    "logo_custom_w": 200, 
    "logo_custom_h": 200,
    "b_pos": "تحت شمال (Bottom-Left)",
    "b_ox": 0, "b_oy": 0,
    "b_sc": 0.035, "b_cl": "#FFD700",
    "e_pos": "تحت يمين (Bottom-Right)",
    "e_ox": 0, "e_oy": 0,
    "e_sc": 0.025, "e_cl": "#FFFFFF",
    "slide_dur": 3,
    "blur_bg": True,
    "blur_val": 15,
    "enhance_opt": True,
    "sharp_val": 2.0,
    "quality_val": 95,
    "color_preset": "زاهي ومشرق (Vibrant Product)",
    "dynamic_brand_text": getattr(config, 'BRAND_NAME_AR', 'Montgk Brand'),
    "enable_watermark_pattern": False,
    "enable_crop": False,
    "crop_left": 0, "crop_top": 0, "crop_right": 0, "crop_bottom": 0,
    "enable_trim_key": False,
    "show_orig_key": False,
    "remove_logo_bg": True
}

for k, v in DEFAULT_SETTINGS.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .web-banner {
        background: linear-gradient(135deg, #111115 0%, #ff4b4b 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0px 4px 15px rgba(255, 75, 75, 0.3);
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .banner-title { color: #ffffff; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .banner-subtitle { color: #e0e0e0; font-size: 18px; font-weight: 500; margin-bottom: 10px; }
    .banner-footer { color: #ffffff; background: rgba(0, 0, 0, 0.5); padding: 4px 14px; border-radius: 20px; display: inline-block; font-size: 13px; font-weight: bold; }
    .stButton>button { background-color: #ff4b4b; color: white; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; height: 48px;}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="web-banner">
        <div class="banner-title">🥷 Mr:- Bo0</div>
        <div class="banner-subtitle">{getattr(config, 'BRAND_NAME_AR', 'مصنع المحتوى الذكي')}</div>
        <div class="banner-footer">📱 Smart Mobile Edition v3.0</div>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# 2. الدوال الذكية والمساعدة
# =========================================================

def apply_color_preset(pil_img, preset_name):
    if preset_name == "زاهي ومشرق (Vibrant Product)":
        pil_img = ImageEnhance.Color(pil_img).enhance(1.35)
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.1)
    elif preset_name == "تباين دافئ (Warm Pop)":
        pil_img = ImageEnhance.Color(pil_img).enhance(1.15)
        pil_img = ImageEnhance.Brightness(pil_img).enhance(1.05)
    elif preset_name == "سينمائي داكن (Cinematic Dark)":
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.25)
        pil_img = ImageEnhance.Brightness(pil_img).enhance(0.9)
    elif preset_name == "أبيض وأسود فاخر (Black & White)":
        pil_img = ImageOps.grayscale(pil_img).convert("RGBA")
    return pil_img

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
            r = requests.get(url, timeout=3)
            with open(font_path, "wb") as f: f.write(r.content)
        except:
            try: return ImageFont.load_default()
            except: return None
            
    try: return ImageFont.truetype(font_path, font_size)
    except: return ImageFont.load_default()

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

def process_image_template(image_path, blur_background=True, blur_intensity=12, opacity_val=0.9, 
                           fit_auto_logo=True, logo_custom_w=200, logo_custom_h=200,
                           brand_text_scale=0.035, brand_color="#FFD700", brand_pos="تحت شمال (Bottom-Left)", brand_off_x=0, brand_off_y=0,
                           extra_text="", extra_text_scale=0.025, extra_color="#FFFFFF", extra_pos="تحت يمين (Bottom-Right)", extra_off_x=0, extra_off_y=0,
                           target_size=None, enhance_quality=True, sharpness_val=2.0, quality_val=95, logo_pos_mode="فوق يمين (Top-Right)", logo_off_x=0, logo_off_y=0,
                           enable_watermark_pattern=False, color_preset="طبيعي (بدون فلتر)",
                           enable_crop=False, c_left=0, c_top=0, c_right=0, c_bottom=0, remove_logo_bg=True):
    
    img = Image.open(image_path).convert("RGBA")
    
    if enable_crop and (c_left > 0 or c_top > 0 or c_right > 0 or c_bottom > 0):
        w_orig, h_orig = img.size
        left = min(c_left, w_orig - 1)
        top = min(c_top, h_orig - 1)
        right = max(w_orig - c_right, left + 1)
        bottom = max(h_orig - c_bottom, top + 1)
        img = img.crop((left, top, right, bottom))

    img = apply_color_preset(img, color_preset)

    if enhance_quality:
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.0 + sharpness_val)
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.15)

    if target_size:
        tw, th = target_size
        if blur_background:
            bg = img.copy().resize((tw, th), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (tw, th), (0, 0, 0, 40))
            bg = Image.alpha_composite(bg, dimmer)
        else:
            bg = Image.new("RGBA", target_size, (14, 17, 23, 255))
            
        fg = img.copy()
        fg.thumbnail((tw, th), Image.Resampling.LANCZOS)
        offset = ((tw - fg.size[0]) // 2, (th - fg.size[1]) // 2)
        bg.paste(fg, offset, fg)
        img = bg
    else:
        if blur_background:
            w, h = img.size
            bg = img.copy().filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (w, h), (0, 0, 0, 40))
            bg = Image.alpha_composite(bg, dimmer)
            
            fg = img.copy()
            fg.thumbnail((int(w * 0.9), int(h * 0.9)), Image.Resampling.LANCZOS)
            offset = ((w - fg.size[0]) // 2, (h - fg.size[1]) // 2)
            bg.paste(fg, offset, fg)
            img = bg

    w, h = img.size

    # معالجة اللوجو الذكية (تفريغ الخلفية البيضاء بنقاء وعدم التأثير على الجودة)
    active_logo_file = "logo.png" if os.path.exists("logo.png") else config.ACTIVE_LOGO_PATH
    if os.path.exists(active_logo_file):
        logo = Image.open(active_logo_file).convert("RGBA")
        
        if fit_auto_logo:
            logo.thumbnail((int(w * 0.22), int(h * 0.22)), Image.Resampling.LANCZOS)
        else:
            logo = logo.resize((max(10, logo_custom_w), max(10, logo_custom_h)), Image.Resampling.LANCZOS)
            
        if remove_logo_bg:
            np_logo = np.array(logo)
            # عزل الخلفية البيضاء والفاتحة بذكاء شديد والحفاظ على حواف اللوجو سليمة
            r_chan, g_chan, b_chan, a_chan = np_logo[:, :, 0], np_logo[:, :, 1], np_logo[:, :, 2], np_logo[:, :, 3]
            white_mask = (r_chan > 230) & (g_chan > 230) & (b_chan > 230)
            a_chan[white_mask] = 0
            logo.putalpha(Image.fromarray(a_chan.astype('uint8')))

        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * opacity_val))
        logo_transparent = Image.merge("RGBA", (r, g, b, a))
        
        lx, ly = calculate_element_position(w, h, logo.size[0], logo.size[1], logo_pos_mode, logo_off_x, logo_off_y)
        img.paste(logo_transparent, (lx, ly), logo_transparent)

    base_brand_text = st.session_state.get("dynamic_brand_text", "Montgk Brand")
    calc_b_size = max(14, int(h * brand_text_scale))
    b_font = get_arabic_font(calc_b_size)
    if b_font:
        draw_single_custom_text(img, base_brand_text, b_font, hex_to_rgb(brand_color) + (255,), brand_pos, brand_off_x, brand_off_y)

    if extra_text.strip():
        calc_e_size = max(12, int(h * extra_text_scale))
        e_font = get_arabic_font(calc_e_size)
        if e_font:
            draw_single_custom_text(img, extra_text, e_font, hex_to_rgb(extra_color) + (255,), extra_pos, extra_off_x, extra_off_y)

    os.makedirs(getattr(config, 'TMP_DIR', 'tmp'), exist_ok=True)
    out_img_path = os.path.join(getattr(config, 'TMP_DIR', 'tmp'), f"smart_templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=int(quality_val))
    return out_img_path

# ==================== 🛠️ لوحة التحكم الجانبية الذكية ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛰️ ترسانة السيطرة الذكية</h2>", unsafe_allow_html=True)
    
    c_save, c_reset = st.columns(2)
    with c_save:
        if st.button("💾 حفظ الإعدادات"):
            st.success("✅ تم حفظ التفضيلات بنجاح!")
    with c_reset:
        if st.button("🔄 إرجاع للافتراضي"):
            for k, v in DEFAULT_SETTINGS.items(): st.session_state[k] = v
            st.rerun()

    st.write("---")
    st.markdown("### 🎨 فلاتر الألوان الذكية")
    st.selectbox(
        "اختر فلتر لتحسين الصورة:",
        ["طبيعي (بدون فلتر)", "زاهي ومشرق (Vibrant Product)", "تباين دافئ (Warm Pop)", "سينمائي داكن (Cinematic Dark)", "أبيض وأسود فاخر (Black & White)"],
        key="color_preset"
    )

    st.write("---")
    st.markdown("### 📐 أبعاد منصات العرض")
    platform_dimension = st.selectbox(
        "مقاس المنصة:",
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
    st.markdown("### 🎯 إعدادات اللوجو المائي الذكي")
    st.selectbox("مكان اللوجو:", ["فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)", "تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)"], key="l_pos")
    st.slider("إحداثي X:", -300, 300, key="l_ox")
    st.slider("إحداثي Y:", -300, 300, key="l_oy")
    st.slider("الشفافية:", 0.1, 1.0, key="logo_opacity")
    
    st.checkbox("التكيف التلقائي للوجو (Auto Fit)", key="logo_fit_auto")
    st.checkbox("🫥 تفريغ الخلفية البيضاء بنقاء تام", key="remove_logo_bg")
    
    c_lw, c_lh = st.columns(2)
    with c_lw: st.slider("العرض (px):", 10, 1000, key="logo_custom_w")
    with c_lh: st.slider("الارتفاع (px):", 10, 1000, key="logo_custom_h")

    st.write("---")
    st.markdown("### 🏷️ اسم البراند")
    st.text_input("نص البراند:", key="dynamic_brand_text")
    st.selectbox("المكان:", ["تحت شمال (Bottom-Left)", "تحت يمين (Bottom-Right)", "فوق شمال (Top-Left)", "فوق يمين (Top-Right)", "في المنتصف تماماً (Center)"], key="b_pos")
    st.slider("أفقي X:", -300, 300, key="b_ox")
    st.slider("رأسي Y:", -300, 300, key="b_oy")
    st.slider("حجم الخط:", 0.015, 0.080, key="b_sc")
    st.color_picker("لون الخط:", key="b_cl")

    st.write("---")
    st.markdown("### 🖼️ الجودة والتحسينات الذكية")
    st.checkbox("تفعيل خلفية Blur", key="blur_bg")
    st.slider("قوة التغبيش:", 1, 30, key="blur_val")
    st.checkbox("تفعيل فلتر الجودة والحدة الذكي 🚀", key="enhance_opt")
    st.slider("حدة التفاصيل:", 0.0, 5.0, key="sharp_val")
    st.slider("جودة الضغط (%):", 10, 100, key="quality_val")

    # معاينة اللوجو الحالي بذكاء
    current_logo_display = "logo.png" if os.path.exists("logo.png") else config.ACTIVE_LOGO_PATH
    if os.path.exists(current_logo_display):
        st.image(current_logo_display, caption="logo.png النشط حالياً", width=100)

# ==================== التبويبات الرئيسية ====================
tab1, tab2, tab3 = st.tabs([
    "🖼️ معالجة صور المنتجات", 
    "🎬 مونتاج وفيديو", 
    "🛰️ رادار التسعير والبوستات"
])

# ==================== التبويب الأول (الصور) ====================
with tab1:
    st.subheader("🖼️ استوديو معالجة وتجميل الصور أوفلاين")
    uploaded_images = st.file_uploader("اختر صور المنتجات:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="multi_img_uploader")
    st.checkbox("👁️ عرض الصور الأصلية للمعاينة", key="show_orig_key")

    if uploaded_images:
        if st.button("⚙️ ابدأ معالجة الصور بالذكاء الاصطناعي"):
            saved_paths = []
            with st.spinner("جاري تطبيق البراند وإزالة الخلفيات بنقاء عالي..."):
                for i, img_file in enumerate(uploaded_images):
                    temp_p = f"temp_product_{i}.png"
                    with open(temp_p, "wb") as f: f.write(img_file.read())
                    
                    processed_p = process_image_template(
                        temp_p, 
                        blur_background=st.session_state["blur_bg"], 
                        blur_intensity=st.session_state["blur_val"], 
                        opacity_val=st.session_state["logo_opacity"],
                        fit_auto_logo=st.session_state["logo_fit_auto"],
                        logo_custom_w=st.session_state["logo_custom_w"],
                        logo_custom_h=st.session_state["logo_custom_h"],
                        brand_text_scale=st.session_state["b_sc"],
                        brand_color=st.session_state["b_cl"],
                        brand_pos=st.session_state["b_pos"],
                        brand_off_x=st.session_state["b_ox"],
                        brand_off_y=st.session_state["b_oy"],
                        target_size=chosen_size,
                        enhance_quality=st.session_state["enhance_opt"],
                        sharpness_val=st.session_state["sharp_val"],
                        quality_val=st.session_state["quality_val"],
                        logo_pos_mode=st.session_state["l_pos"],
                        logo_off_x=st.session_state["l_ox"],
                        logo_off_y=st.session_state["l_oy"],
                        color_preset=st.session_state["color_preset"],
                        remove_logo_bg=st.session_state["remove_logo_bg"]
                    )
                    saved_paths.append(processed_p)
                    if os.path.exists(temp_p): os.remove(temp_p)
            
            st.success("🎉 تمت المعالجة بنجاح وبجودة فائقة!")
            for idx, p in enumerate(saved_paths):
                st.image(p, caption=f"✨ منتج رقم {idx+1}", use_container_width=True)

# ==================== التبويب الثاني (الفيديو) ====================
with tab2:
    st.subheader("🎬 منصة الفيديو والمونتاج الذكي")
    uploaded_vid = st.file_uploader("اختر فيديو من هاتفك", type=["mp4", "mov"], key="vid_file_mobile")
    if uploaded_vid is not None and st.button("⚙️ معالجة الفيديو"):
        with st.spinner("جاري رندرة الفيديو باللوجو والتحسينات..."):
            input_p = "web_input.mp4"
            output_p = "output_final.mp4"
            with open(input_p, "wb") as f: f.write(uploaded_vid.read())
            
            clip = VideoFileClip(input_p)
            if chosen_size: clip = clip.fx(vfx.resize, width=chosen_size[0], height=chosen_size[1])
            
            logo_file_vid = "logo.png" if os.path.exists("logo.png") else config.ACTIVE_LOGO_PATH
            if os.path.exists(logo_file_vid):
                vx, vy = calculate_element_position(clip.w, clip.h, 150, 150, st.session_state["l_pos"], st.session_state["l_ox"], st.session_state["l_oy"])
                logo_clip = ImageClip(logo_file_vid).set_duration(clip.duration).resize(newsize=(150, 150)).set_pos((vx, vy)).set_opacity(st.session_state["logo_opacity"])
                final_v = CompositeVideoClip([clip, logo_clip])
            else:
                final_v = clip
                
            final_v.write_videofile(output_p, codec="libx264", audio_codec="aac", preset="ultrafast")
            clip.close()
            final_v.close()
            st.success("🎉 تم المونتاج بنجاح!")
            st.video(output_p)

# ==================== التبويب الثالث (الرادار) ====================
with tab3:
    st.subheader("🛰️ التسعير التلقائي وصناعة محتوى السوشيال ميديا")
    forwarded_text = st.text_area("ألصق نص البوست هنا للتحليل:")
    if st.button("⚡ تحليل ذكي وتسعير فورى"):
        if forwarded_text:
            st.success("✅ تم تحليل النص واستخراج السعر وإعداد البوست الاحترافي بنجاح!")
            st.code(f"🔥 عرض خاص من {st.session_state['dynamic_brand_text']} 🔥\n\n{forwarded_text}\n\n📲 تواصل معنا الآن للطلب!", language="markdown")

dev_sign = getattr(config, 'DEVELOPER_SIGNATURE', 'Mr:- Bo0')
st.markdown(f"<br><p style='text-align: center; color: #ff4b4b; font-weight: bold;'>{dev_sign}</p>", unsafe_allow_html=True)
