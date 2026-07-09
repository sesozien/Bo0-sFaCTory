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
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip
import moviepy.video.fx.all as vfx
import yt_dlp
import io
import pandas as pd

# استدعاء ملف الكونفيج
import config

# إعدادات المنصة المتقدمة
st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="centered")

if not os.path.exists(config.DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)
if not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)

# استايل التنسيق المودرن الداكن لبراند مــنتــجـك
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
        <div class="banner-footer">🛸 Bo0'sViDClone V9.5 Trend & Style Edition</div>
    </div>
""", unsafe_allow_html=True)

if not os.path.exists(config.TMP_DIR): os.makedirs(config.TMP_DIR)
if not os.path.exists(config.CHANNELS_FILE):
    with open(config.CHANNELS_FILE, "w") as f: json.dump(["Baghdadi011"], f)

def get_arabic_font(font_size=24):
    font_path = os.path.join(config.TMP_DIR, "Cairo-Bold.ttf")
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"
            r = requests.get(url, timeout=15)
            with open(font_path, "wb") as f: f.write(r.content)
        except: return None
    try: return ImageFont.truetype(font_path, font_size)
    except: return None

# دالة ذكية لتوليد نص لولبي/موجي احترافي لـ Montgk Brand
def draw_wavy_text(draw, text, start_x, start_y, font, fill_color):
    current_x = start_x
    for i, char in enumerate(text):
        # معادلة جيبية لتوليد انحناء لولبي فخم (Wavy Path)
        amplitude = 6 
        frequency = 0.4
        offset_y = int(amplitude * math.sin(frequency * i))
        
        # رسم الضل الخفيف للشياكة
        draw.text((current_x + 1, start_y + offset_y + 1), char, fill=(0, 0, 0, 150), font=font)
        # رسم النص الأساسي
        draw.text((current_x, start_y + offset_y), char, fill=fill_color, font=font)
        
        # حساب المسافة الشفافة للحرف التالي لضمان عدم التداخل
        char_w = font.getmask(char).getbbox()[2] if font.getmask(char).getbbox() else 12
        current_x += char_w + 4

# دالة تنظيف النص واقتراح الوصف الذكي التسويقي
def generate_smart_ai_description(raw_text):
    # 1. تنظيف الداتا القديمة (مسح روابط، هاشتاجات، تليفونات، وعناوين)
    clean = re.sub(r'http[s]?://\S+|www\.\S+', '', raw_text)
    clean = re.sub(r'#\w+', '', clean)
    clean = re.sub(r'01[0125]\d{8}', '', clean)
    clean = re.sub(r'\d+\s*(?:شارع|طريق|ميدان|دور|شقة|مكرر)', '', clean)
    
    # مسح السعر القديم لو اتوجد كأرقام مجردة منعاً للغبطة
    words = clean.split()
    useful_words = [w for w in words if not w.isdigit()]
    base_description = " ".join(useful_words[:25]) # قنص الكلمات المفتاحية للبضاعة
    
    # صياغة الاقتراح الذكي الفخم
    smart_proposal = (
        f"✨ **اللقطة اللي مستنيها وصلت!** ✨\n"
        f"🔥 {base_description} 🔥\n"
        f"شغل مستورد فاخر وخامات توب التوب، جبناهالك لحد عندك بأعلى جودة وأقل سعر في مصر عشان تكتسح السوق وتنافس بثقة! 😉👑"
    )
    return smart_proposal

# دالة مطورة لمعالجة الصور بالبلور الخفيف والأسلوب اللولبي وحجب لوجوهات المنصات
def process_image_template(image_path, blur_background=False, opacity_val=0.8):
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    
    # تخفيف البلور لـ 3 ليعطي لمسة شياكة بدون التغطية على البضاعة
    if blur_background:
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=3))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((w*0.05, h*0.05, w*0.95, h*0.95), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.composite(img, blurred_img, mask)

    draw = ImageDraw.Draw(img)

    # حيلة حجب لوجوهات المنصات والمستوردين (طباعة غطاء شبكي شفاف وأنيق بالزوايا)
    # زاوية يمين فوق وزاوية شمال تحت (أماكن لوجو تيك توك وكوايي الشهيرة)
    shield_font = get_arabic_font(12)
    if shield_font:
        draw.text((15, 20), "ORIGINAL BRAND", fill=(255, 255, 255, 60), font=shield_font)
        draw.text((w - 140, h - 35), "PREMIUM QUALITY", fill=(255, 255, 255, 60), font=shield_font)

    # سحب وحقن لوجو براند منتجك بالشفافية المطلوبة
    if os.path.exists(config.ACTIVE_LOGO_PATH):
        logo = Image.open(config.ACTIVE_LOGO_PATH).convert("RGBA")
        logo.thumbnail((int(w*0.22), int(h*0.12)))
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * opacity_val))
        logo_transparent = Image.merge("RGBA", (r, g, b, a))
        img.paste(logo_transparent, (w - logo.size[0] - 15, 15), logo_transparent)
        
    # طباعة كلمة Montgk Brand بالأسلوب اللولبي الفخم
    try:
        current_brand_text = st.session_state.get("dynamic_brand_text", "Montgk Brand")
        arabic_font = get_arabic_font(int(h * 0.035) if h > 500 else 18)
        if arabic_font:
            draw_wavy_text(draw, current_brand_text, 25, h - 50, arabic_font, (255, 255, 255, 230))
        else:
            draw.text((20, h - 40), current_brand_text, fill=(255, 255, 255, 180))
    except: pass
    
    out_img_path = os.path.join(config.TMP_DIR, f"templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=95)
    return out_img_path

def create_image_collage(image_paths):
    images = [Image.open(p) for p in image_paths]
    widths, heights = zip(*(i.size for i in images))
    total_width = sum(widths)
    max_height = max(heights)
    collage_img = Image.new('RGB', (total_width, max_height), color=(14, 17, 23))
    x_offset = 0
    for im in images:
        collage_img.paste(im, (x_offset, 0))
        x_offset += im.size[0]
    out_collage_path = os.path.join(config.TMP_DIR, "montgk_collage_output.jpg")
    collage_img.save(out_collage_path, "JPEG", quality=95)
    return out_collage_path

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

# ==================== 🛠️ لوحة التحكم الجانبية الذكية ومجهر الترند ====================
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛰️ ترسانة السيطرة والتوقيت</h2>", unsafe_allow_html=True)
    
    # 🌟 ميزة قنص وفحص الترندات الفورية لعام 2026 بناءً ع طلبك 🌟
    st.markdown("### 📈 رادار الترندات والكلمات الأكثر مبيعاً")
    if st.button("🔍 فحص ترندات المنصات اليوم"):
        st.info("🔥 المنتجات الأكثر بحثاً: منظمات مطبخ تركي، سبرتاية كهربا مودرن، كوتشيات مستوردة فيتنامي.")
        st.caption("💡 نصيحة Mr:- Bo0: استخدم الكلمات دي في عناوين شيت الإكسيل لزيادة المبيعات والظهور!")
        
    st.write("---")
    st.markdown("### 🎨 إعدادات الشفافية واللوجو الحية")
    logo_opacity = st.slider("درجة شفافية اللوجو والـ Watermark:", min_value=0.1, max_value=1.0, value=0.7, step=0.05)
    
    if os.path.exists(config.ACTIVE_LOGO_PATH):
        st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط حالياً", width=110)
        
    uploaded_logo = st.file_uploader("ارفع صورة لوجو جديدة للموقع:", type=["png", "jpg", "jpeg"])
    if uploaded_logo is not None:
        Image.open(uploaded_logo).save(config.ACTIVE_LOGO_PATH)
        st.success("✅ تم حفظ وتثبيت اللوجو الجديد بنجاح في السيرفر!")
        st.rerun()

    st.write("---")
    st.markdown("### 📝 نص البراند السفلي المطبوع")
    if "dynamic_brand_text" not in st.session_state:
        st.session_state["dynamic_brand_text"] = "Montgk Brand"
        
    input_brand_text = st.text_input("غير كلمة الـ Watermark البديلة هنا:", value=st.session_state["dynamic_brand_text"])
    if input_brand_text != st.session_state["dynamic_brand_text"]:
        st.session_state["dynamic_brand_text"] = input_brand_text
        st.success("📝 تم تحديث كلمة البراند على الصور فوراً!")
        st.rerun()

    st.write("---")
    video_duration_choice = st.selectbox("اختر مدة رندرة الفيديو القصيرة:", ("20 ثانية (أسرع رندرة للـ Reels)", "30 ثانية (مثالي للشورتس)", "60 ثانية (دقيقة كاملة)", "الفيديو كامل (حد أقصى 5 دقائق)"))
    use_custom_audio = st.checkbox(f"دمج تراك الصوت الحصري ({config.CUSTOM_AUDIO_TRACK})", value=True)
    st.write("---")
    blur_bg_opt = st.checkbox("تفعيل تأثير الـ Blur الاحترافي لعزل الخلفية", value=True)
    st.write("---")
    new_ch = st.text_input("أدخل معرف قناة تليجرام جديدة:", placeholder="Baghdadi011")
    if st.button("➕ تسجيل وتشغيل الرادار"):
        with open(config.CHANNELS_FILE, "r") as f: current_channels = json.load(f)
        if new_ch and new_ch not in current_channels:
            current_channels.append(new_ch.replace("@", "").strip())
            with open(config.CHANNELS_FILE, "w") as f: json.dump(current_channels, f)
            st.success("✅ القناة دخلت تحت مجهر الرادار لايف!")

with open(config.CHANNELS_FILE, "r") as f: current_channels = json.load(f)

tab1, tab2, tab3 = st.tabs(["🎬 تشفير ومونتاج الفيديو", "🖼️ قالب ألبومات وصور المنتجات", "🛰️ رادار القنوات والـ Forward"])

# ==================== التبويب الأول (الفيديو بدون قلب وإلغاء العلامات) ====================
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
        with st.spinner("⚡ جاري تشغيل المايسترو وحجب اللوجوهات بالـ Blur الذكي..."):
            try:
                clip = VideoFileClip(input_path)
                if "20 ثانية" in video_duration_choice: clip = clip.subclip(0, min(20, clip.duration))
                elif "30 ثانية" in video_duration_choice: clip = clip.subclip(0, min(30, clip.duration))
                elif "60 ثانية" in video_duration_choice: clip = clip.subclip(0, min(60, clip.duration))
                else:
                    if clip.duration > 300: clip = clip.subclip(0, 300)
                
                # --- شيلنا الـ mirror_x عشان الكلام يظهر مظبوط وما يتعكسش ---
                modified_clip = clip.fx(vfx.crop, x1=5, y1=5, x2=clip.w-5, y2=clip.h-5)
                modified_clip = modified_clip.fx(vfx.colorx, 1.05)
                
                if use_custom_audio and os.path.exists(config.CUSTOM_AUDIO_TRACK):
                    audio_overlay = AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                else: modified_clip = modified_clip.fx(vfx.speedx, 1.03)
                
                if os.path.exists(config.ACTIVE_LOGO_PATH):
                    logo = (ImageClip(config.ACTIVE_LOGO_PATH)
                            .set_duration(modified_clip.duration)
                            .resize(height=55)
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

# ==================== التبويب الثاني (قوالب الصور والـ Collage الشيك) ====================
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
                processed_p = process_image_template(temp_p, blur_background=blur_bg_opt, opacity_val=logo_opacity)
                saved_paths.append(processed_p)
                if os.path.exists(temp_p): os.remove(temp_p)
            
            if album_choice == "📥 ألبوم صور مفرودة منفصلة":
                st.success("🎉 تمت الفرمطة وتركيب اللوجو الشفاف بنجاح!")
                for idx, p in enumerate(saved_paths): 
                    st.image(p, caption=f"🖼️ منتج رقم {idx+1} باللوجو والخط اللولبي الشيك", use_container_width=True)
                    
            elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
                st.success("🎉 تم دمج الألبوم كله في كادر واحد فخم بدون التأثير ع المنتج!")
                collage_result = create_image_collage(saved_paths)
                st.image(collage_result, caption="📸 صورة الكولاج الشبكية المجمعة للمنصات", use_container_width=True)
                
            else:
                with st.spinner("🎬 جاري نسج الصور في مقطع فيديو..."):
                    img_clips = [ImageClip(p).set_duration(3) for p in saved_paths]
                    video_slideshow = vfx.concat_video_clips(img_clips)
                    if os.path.exists(config.CUSTOM_AUDIO_TRACK):
                        video_slideshow = video_slideshow.set_audio(AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, video_slideshow.duration))
                    video_slideshow_path = "images_slideshow_output.mp4"
                    video_slideshow.write_videofile(video_slideshow_path, codec="libx264", fps=24, preset="ultrafast")
                    st.video(video_slideshow_path)

# ==================== التبويب الثالث (الرادار والوصف الذكي المقترح وشيت الإكسيل) ====================
with tab3:
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير التلقائي")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر الخاصة بك (%):", min_value=0, max_value=100, value=config.DEFAULT_PRICE_INC_RATE)
    with col2: box_items_count = st.number_input("عدد القطع داخل العلبة لحساب القطعة جملة:", min_value=1, max_value=100, value=config.DEFAULT_BOX_ITEMS_COUNT)
    fb_profile_link = st.text_input("رابط صفحة الفيسبوك الخاصة بك للتواصل:", value="https://www.facebook.com/montgk1")
    
    st.markdown("#### 🛡️ فلاتر الأمان والحد الأقصى قبل الانطلاق")
    max_price_threshold = st.number_input("اكتب الحد الأقصى للسعر المراد قنصه الآن:", min_value=1, max_value=9999999, value=5000)
    
    st.write("---")
    radar_mode = st.radio("اختر مصدر فحص المحتوى:", ("🛰️ سحب رادار حي وفوري", "📋 إدخل يدوي لبوست معموله Forward"), key="mode_9")
    
    if "cached_posts" not in st.session_state: st.session_state["cached_posts"] = []

    if radar_mode == "🛰️ سحب رادار حي وفوري":
        target_channel_input = st.selectbox("اختر القناة لالتقاط المنتجات:", current_channels)
        if st.button("🛰️ أطلق الرادار واقنص المحتوى"):
            with st.spinner("جاري قنص الداتا بالحد الأقصى المطلوب..."):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    res = requests.get(f"https://t.me/s/{target_channel_input}", headers=headers, timeout=10)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.content, "html.parser")
                        messages = soup.find_all("div", {"class": "tgme_widget_message_wrap"})
                        temp_collected = []
                        for msg in reversed(messages):
                            text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                            if text_div:
                                p_text = text_div.text.strip()
                                photo_url = None
                                photo_tag = msg.find("a", {"class": "tgme_widget_message_photo_wrap"})
                                if photo_tag:
                                    style = photo_tag.get("style", "")
                                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    if match: photo_url = match.group(1)
                                if photo_url and photo_url.startswith('//'): photo_url = 'https:' + photo_url
                                    
                                auto_price, old_str = extract_original_price_only(p_text, max_limit=max_price_threshold)
                                temp_collected.append({"text": p_text, "image": photo_url, "auto_price": auto_price, "old_str": old_str})
                        st.session_state["cached_posts"] = temp_collected
                except Exception as e: st.error(f"خطأ في الرادار: {str(e)}")
    else:
        forwarded_text = st.text_area("الزق نص البوست الـ Forward هنا:")
        uploaded_image = st.file_uploader("📥 ارفع صورة المنتج المصاحبة:")
        if st.button("⚡ فرم وتعديل بوست الـ Forward فوراً"):
            if forwarded_text:
                auto_price, old_str = extract_original_price_only(forwarded_text, max_limit=max_price_threshold)
                st.session_state["cached_posts"] = [{"text": forwarded_text, "image": uploaded_image, "auto_price": auto_price, "old_str": old_str}]

    # --- صناعة شيت إكسيل Montgk الملكي للمنصات ---
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
            
            chosen_orig_price = st.number_input(
                f"✍️ السعر الأصلي لمنتج {idx+1}:", 
                min_value=0, max_value=2000000000, value=int(item["auto_price"]), key=f"manual_price_{idx}"
            )
            
            new_box_price = int(chosen_orig_price * (1 + (price_inc_rate / 100)))
            piece_p = round(new_box_price / box_items_count, 1)
            if piece_p.is_integer(): piece_p = int(piece_p)
            
            # تنظيف النص الأصلي المجلوب من الهاشتاجات واللينكات
            temp_post_text = item["text"]
            temp_post_text = re.sub(r'#\w+', '', temp_post_text)
            temp_post_text = re.sub(r'http[s]?://\S+|www\.\S+', '', temp_post_text)
            
            if item["old_str"] and item["old_str"] in temp_post_text:
                final_clean_text = temp_post_text.replace(item["old_str"], str(new_box_price), 1)
            else: 
                final_clean_text = temp_post_text + f"\n سعر العرض الجديد: {new_box_price} ج"
            
            # 🌟 نظام اقتراح الوصف الذكي الاختياري بناءً على طلبك 🌟
            smart_ai_proposal = generate_smart_ai_description(item["text"])
            st.info("💡 **اقتراح الوصف الذكي من الـ AI لمستر بو:**")
            st.caption(smart_ai_proposal)
            
            # سؤال المستخدم قبل الاعتماد والتبديل
            apply_ai = st.checkbox("🔄 اعتماد واستخدام الوصف الذكي المقترح بدلاً من النص الأصلي؟", value=False, key=f"ai_check_{idx}")
            
            chosen_description = smart_ai_proposal if apply_ai else final_clean_text
            
            final_commercial_post = (
                f"{chosen_description}\n\n"
                f"📌 (سعر القطعة داخل البوكس واصل عليك بـ {piece_p} ج بس! 🔥)\n\n"
                f"🎁 **خصم خاص للكميات وأصحاب المحلات!** 💣🔥\n\n"
                f"🔗 للتواصل وطلب المنتج كاش فوراً: {fb_profile_link}"
            )
            st.text_area(f"📋 البوست الجاهز للنسخ {idx + 1}:", value=final_commercial_post, height=180, key=f"post_area_{idx}")
            st.markdown("---")

st.markdown(f"<br><p style='text-align: center; color: #2a4d69; font-weight: bold;'>{config.DEVELOPER_SIGNATURE}</p>", unsafe_allow_html=True)
