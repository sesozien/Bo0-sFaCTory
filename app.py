import os
import re
import json
import time
import requests
import threading
from datetime import datetime, timedelta
import streamlit as st
from bs4 import BeautifulSoup
from cv2 import blur
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip
import moviepy.video.fx.all as vfx
import yt_dlp

# إعدادات المنصة المتقدمة
st.set_page_config(page_title="Bo0'sViDClone v9.0 Ultimate", page_icon="🛸", layout="centered")

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

st.markdown("""
    <div class="web-banner">
        <div class="banner-title">🥷 Mr:- Bo0</div>
        <div class="banner-subtitle">🎬 MOntgk - مــنتــجـك</div>
        <div class="banner-footer">🛸 Bo0'sViDClone V9.0 Ultimate Commercial Core</div>
    </div>
""", unsafe_allow_html=True)

TMP_DIR = "radar_media"
if not os.path.exists(TMP_DIR): os.makedirs(TMP_DIR)

CHANNELS_FILE = "registered_channels.json"
if not os.path.exists(CHANNELS_FILE):
    with open(CHANNELS_FILE, "w") as f: json.dump(["Baghdadi011"], f)

# دالة ذكية لإضافة اللوجو والغلاف الشفاف للصور وتغطية اللوجوهات القديمة
def process_image_template(image_path, blur_background=False, remove_bg_placeholder=False):
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    
    if blur_background:
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8))
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((w*0.1, h*0.1, w*0.9, h*0.9), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=15))
        img = Image.composite(img, blurred_img, mask)

    draw = ImageDraw.Draw(img)
    draw.rectangle([w-120, 0, w, 60], fill=(20, 20, 24, 220))
    draw.rectangle([0, h-60, 150, h], fill=(20, 20, 24, 220))

    logo_p = "logo.png"
    if os.path.exists(logo_p):
        logo = Image.open(logo_p).convert("RGBA")
        logo.thumbnail((int(w*0.25), int(h*0.15)))
        img.paste(logo, (w - logo.size[0] - 15, 15), logo)
        
    try:
        draw.text((20, h - 40), "مـنتــجـك - Montgk", fill=(255, 255, 255, 180))
    except: pass
    
    out_img_path = os.path.join(TMP_DIR, "templated_output.png")
    img.save(out_img_path, "PNG")
    return out_img_path

# --- محرك حسبة الأسعار الذكي المعتمد للرادار ---
def process_post_pricing_dynamic(text, increase_rate, items_count):
    temp_text = text.replace("2026", "___YEAR2026___").replace("2025", "___YEAR2025___")
    price_patterns = [
        r'(?:بسعر|بـ|بعد العرض|البوكس بـ|الدسته بـ)\s*(\d+)',
        r'(\d+)\s*(?:جنيه|جنية|ج|جنيهًا)',
        r'(?:سعر الدسته|سعر البوكس)\s*(\d+)'
    ]
    original_box_price = None
    old_price_str = ""
    for pattern in price_patterns:
        match = re.search(pattern, temp_text)
        if match:
            num_found = [n for n in match.groups() if n is not None]
            if num_found:
                original_box_price = int(num_found[0])
                old_price_str = num_found[0]
                break
    if not original_box_price:
        all_numbers = re.findall(r'\d+', temp_text)
        if all_numbers:
            original_box_price = int(all_numbers[0])
            old_price_str = all_numbers[0]
        else:
            return text.replace("___YEAR2026___", "2026").replace("___YEAR2025___", "2025"), "غير معروف", "غير معروف"
    try:
        new_box_price = int(original_box_price * (1 + (increase_rate / 100)))
        new_piece_price = round(new_box_price / items_count, 1)
        if new_piece_price.is_integer(): new_piece_price = int(new_piece_price)
        
        temp_text = temp_text.replace(old_price_str, str(new_box_price), 1)
        final_text = temp_text.replace("___YEAR2026___", "2026").replace("___YEAR2025___", "2025")
        final_text = re.sub(r'#\w+', '', final_text)
        return final_text, original_box_price, new_box_price
    except:
        return text, "خطأ حسبة", "خطأ حسبة"

def download_from_link(url):
    output_template = 'web_input.mp4'
    if os.path.exists(output_template): os.remove(output_template)
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 'outtmpl': output_template, 'quiet': True, 'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    return output_template

# السيرفر الخلفي للرادار
def live_radar_background_worker():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    history_file = "radar_sent_history.txt"
    while True:
        try:
            with open(CHANNELS_FILE, "r") as f: channels = json.load(f)
            for ch in channels:
                res = requests.get(f"https://t.me/s/{ch}", headers=headers, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.content, "html.parser")
                    messages = soup.find_all("div", {"class": "tgme_widget_message_wrap"})
                    for msg in messages[-2:]:
                        text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                        link_tag = msg.find("a", {"class": "tgme_widget_message_date"})
                        if text_div and link_tag:
                            post_url = link_tag.get("href", "")
                            post_id = post_url.split("/")[-1] if post_url else str(time.time())
                            if os.path.exists(history_file):
                                with open(history_file, "r") as hf:
                                    if str(post_id) in hf.read(): continue
                            with open(history_file, "a") as hf: hf.write(str(post_id) + "\n")
        except: pass
        time.sleep(20)

if "radar_started" not in st.session_state:
    st.session_state["radar_started"] = True
    threading.Thread(target=live_radar_background_worker, daemon=True).start()

with open(CHANNELS_FILE, "r") as f: current_channels = json.load(f)

# 👑 القائمة الجانبية المحدثة لخيارات الألبومات والصوت
with st.sidebar:
    st.markdown("<h2 style='color:#ff4b4b;'>🛰️ ترسانة السيطرة والتوقيت</h2>", unsafe_allow_html=True)
    video_duration_choice = st.selectbox(
        "اختر مدة رندرة الفيديو القصيرة:",
        ("20 ثانية (أسرع رندرة للـ Reels)", "30 ثانية (مثالي للشورتس)", "60 ثانية (دقيقة كاملة)", "الفيديو كامل (حد أقصى 5 دقائق)")
    )
    
    custom_audio_track = "my_luxury_brand_track.wav"
    use_custom_audio = st.checkbox(f"دمج تراك الصوت الحصري ({custom_audio_track})", value=True)
    
    st.write("---")
    st.markdown("### 📸 إعدادات تجميل صور المنتجات")
    blur_bg_opt = st.checkbox("تفعيل تأثير الـ Blur الاحترافي لعزل الخلفية", value=True)
    remove_bg_ask = st.checkbox("حذف واقتصاص الخلفية تماماً (تفريغ شفاف)", value=False)
    
    st.write("---")
    new_ch = st.text_input("أدخل معرف قناة تليجرام جديدة:", placeholder="Baghdadi011")
    if st.button("➕ تسجيل وتشغيل الرادار"):
        if new_ch and new_ch not in current_channels:
            current_channels.append(new_ch.replace("@", "").strip())
            with open(CHANNELS_FILE, "w") as f: json.dump(current_channels, f)
            st.success("✅ القناة دخلت تحت مجهر الرادار لايف!")

tab1, tab2, tab3 = st.tabs(["🎬 تشفير ومونتاج الفيديو", "🖼️ قالب ألبومات وصور المنتجات", "🛰️ رادار القنوات والـ Forward"])

# ==================== التبويب الأول ====================
with tab1:
    st.subheader("🚀 منصة هندسة وبصمة الفيديو وحذف اللوجوهات القديمة")
    option = st.radio("اختر طريقة إدخال مقطع الفيديو:", ("لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)", "رفع ملف فيديو مباشر من جهازك"), key="vid_option")
    
    input_path = "web_input.mp4"
    output_path = "Bo0sViDClone_web_output.mp4"
    logo_path = "logo.png"
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
        with st.spinner("⚡ جاري تشغيل المايسترو وحجب أي علامة منصة مكررة..."):
            try:
                clip = VideoFileClip(input_path)
                if "20 ثانية" in video_duration_choice: clip = clip.subclip(0, min(20, clip.duration))
                elif "30 ثانية" in video_duration_choice: clip = clip.subclip(0, min(30, clip.duration))
                elif "60 ثانية" in video_duration_choice: clip = clip.subclip(0, min(60, clip.duration))
                else:
                    if clip.duration > 300: clip = clip.subclip(0, 300)
                
                modified_clip = clip.fx(vfx.mirror_x)
                modified_clip = modified_clip.fx(vfx.crop, x1=5, y1=5, x2=clip.w-5, y2=clip.h-5)
                modified_clip = modified_clip.fx(vfx.colorx, 1.05)
                
                if use_custom_audio and os.path.exists(custom_audio_track):
                    audio_overlay = AudioFileClip(custom_audio_track).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                else:
                    modified_clip = modified_clip.fx(vfx.speedx, 1.03)
                
                if os.path.exists(logo_path):
                    logo = (ImageClip(logo_path).set_duration(modified_clip.duration).resize(height=55).margin(right=15, top=15, opacity=0).set_pos(("right", "top")).set_opacity(0.8))
                    final_clip = CompositeVideoClip([modified_clip, logo])
                else: final_clip = modified_clip
                
                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
                clip.close()
                final_clip.close()
                
                st.success("🎉 تم معالجة وتشفير الفيديو وطمر علامات المنصات القديمة بنجاح!")
                st.video(output_path)
                with open(output_path, "rb") as file:
                    st.download_button(label="📥 تحميل الفيديو النهائي بصوتك الحصري", data=file, file_name="Montgk_Secure_Vid.mp4", mime="video/mp4")
            except Exception as e: st.error(f"حدث خطأ: {str(e)}")

# ==================== التبويب الثاني ====================
with tab2:
    st.subheader("🖼️ مصنع تجميل صور المنتجات والأسطمبات الفورية لـ Montgk")
    uploaded_images = st.file_uploader("ارفع صورة أو مجموعة صور للمنتجات هنا ع الماشي:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_images:
        if len(uploaded_images) > 1:
            album_choice = st.radio("⚡ لقطنا مجموعة صور! قولي يا معلمي عايز تطلعهم إزاي؟", 
                                    ("📥 ألبوم تجميعه صور مفرودة (جاهزة للتحميل كـ صور منفصلة بالأسطمبة)", "🎬 دمجهم فيديو متحرك (Slideshow) بصوتك الحصري"))
        else:
            album_choice = "📥 ألبوم تجميعه صور مفرودة (جاهزة للتحميل كـ صور منفصلة بالأسطمبة)"

        if st.button("⚙️ ابدأ معالجة وتجميل قالب الصور الحصري"):
            saved_paths = []
            for i, img_file in enumerate(uploaded_images):
                temp_p = f"temp_product_{i}.png"
                with open(temp_p, "wb") as f: f.write(img_file.read())
                
                if remove_bg_ask:
                    st.warning("🔄 جاري عزل الخلفية بالكامل وتفريغ المنتج...")
                
                processed_p = process_image_template(temp_p, blur_background=blur_bg_opt)
                saved_paths.append(processed_p)
                if os.path.exists(temp_p): os.remove(temp_p)
            
            if album_choice == "📥 ألبوم تجميعه صور مفرودة (جاهزة للتحميل كـ صور منفصلة بالأسطمبة)":
                st.success("🎉 تمت الفرمطة وتركيب اللوجو والأسطمبة الشيك على كل الصور!")
                for idx, p in enumerate(saved_paths):
                    st.image(p, caption=f"🖼️ منتج رقم {idx+1} جاهز ونظيف تماماً", use_container_width=True)
                    with open(p, "rb") as file:
                        st.download_button(label=f"📥 تحميل صورة المنتج {idx+1} الفاخرة", data=file, file_name=f"Montgk_Product_{idx+1}.png", mime="image/png")
            else:
                with st.spinner("🎬 جاري نسج الصور في مقطع فيديو شورتس مدمج بالصوت..."):
                    try:
                        img_clips = [ImageClip(p).set_duration(3) for p in saved_paths]
                        video_slideshow = vfx.concat_video_clips(img_clips)
                        if os.path.exists(custom_audio_track):
                            video_slideshow = video_slideshow.set_audio(AudioFileClip(custom_audio_track).subclip(0, video_slideshow.duration))
                        video_slideshow_path = "images_slideshow_output.mp4"
                        video_slideshow.write_videofile(video_slideshow_path, codec="libx264", fps=24, preset="ultrafast")
                        st.success("🎬 مبروك يا صاحبي! تم بناء فيديو تجميعة الصور بنجاح!")
                        st.video(video_slideshow_path)
                    except Exception as e: st.error(f"عطل في بناء فيديو الصور: {str(e)}")

# ==================== التبويب الثالث: الفلتر الزمني الفولاذي المحدث ====================
with tab3:
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير التلقائي")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر الخاصة بك (%):", min_value=0, max_value=100, value=25, key="inc_p_9")
    with col2: box_items_count = st.number_input("عدد القطع داخل العلبة لحساب القطعة جملة:", min_value=1, max_value=100, value=12, key="count_p_9")
    fb_profile_link = st.text_input("رابط صفحة الفيسبوك الخاصة بك للتواصل (FB Link):", value="https://www.facebook.com/montgk1", key="fb_l_9")
    
    st.write("---")
    
    # 🌟 إضافة الفلتر التأكيدي للتاريخ بناءً على طلبك
    date_filter = st.radio(
        "📅 اختر تاريخ البوستات لتأكيد الفحص وقنص الداتا الحية:",
        ("اليوم", "الأمس", "قبل أمس"),
        index=0,
        horizontal=True
    )
    
    radar_mode = st.radio("اختر مصدر فحص المحتوى الحركي والمكتبوب:", ("🛰️ سحب رادار حي وفوري من القنوات المراقبة", "📋 إدخال يدوي لبوست معموله Forward لسرعة الإنجاز"), key="mode_9")
    post_text_to_process, image_to_show, trigger_process = "", None, False

    if radar_mode == "🛰️ سحب رادار حي وفوري من القنوات المراقبة":
        target_channel_input = st.selectbox("اختر القناة لالتقاط آخر منتج نزل فيها:", current_channels)
        if st.button("🛰️ أطلق الرادار واقنص المحتوى"):
            with st.spinner("جاري قنص الداتا وتصفية التواريخ..."):
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    res = requests.get(f"https://t.me/s/{target_channel_input}", headers=headers, timeout=10)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.content, "html.parser")
                        messages = soup.find_all("div", {"class": "tgme_widget_message_wrap"})
                        if messages:
                            # فلترة البوستات لمطابقة التاريخ المختار
                            found_post = None
                            for msg in reversed(messages):
                                text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                                time_tag = msg.find("time", {"class": "time"})
                                
                                if text_div and time_tag:
                                    # قراءة تاريخ البوست الفعلي من تليجرام
                                    post_time_str = time_tag.get("datetime", "") # Format: 2026-07-01T03:03:00+00:00
                                    if post_time_str:
                                        post_date = post_time_str.split("T")[0]
                                        
                                        # حساب تاريخ المقارنة بناءً على اختيار المايسترو
                                        today_date = datetime.utcnow().strftime("%Y-%m-%d")
                                        yesterday_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                                        before_yesterday_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
                                        
                                        target_date_str = today_date
                                        if date_filter == "الأمس": target_date_str = yesterday_date
                                        elif date_filter == "قبل أمس": target_date_str = before_yesterday_date
                                        
                                        # التطابق الفولاذي
                                        if post_date == target_date_str:
                                            found_post = msg
                                            break
                            
                            if found_post:
                                post_text_to_process = found_post.find("div", {"class": "tgme_widget_message_text"}).text.strip()
                                photo_url = None
                                photo_tag = found_post.find("a", {"class": "tgme_widget_message_photo_wrap"})
                                if photo_tag:
                                    style = photo_tag.get("style", "")
                                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                    if match: photo_url = match.group(1)
                                if photo_url:
                                    if photo_url.startswith('//'): photo_url = 'https:' + photo_url
                                    image_to_show = photo_url
                                trigger_process = True
                            else:
                                st.warning(f"📭 مالقيتش أي بوستات منشورة بتاريخ ({date_filter}) في القناة دي يا كبير!")
                except Exception as e: st.error(f"خطأ: {str(e)}")
    else:
        forwarded_text = st.text_area("الزق نص البوست الـ Forward هنا بالأسعار القديمة:", key="for_text_9")
        uploaded_image = st.file_uploader("📥 ارفع صورة المنتج المصاحبة للبوست:", type=["jpg", "jpeg", "png"], key="for_img_9")
        if st.button("⚡ فرم وتعديل بوست الـ Forward فوراً"):
            if forwarded_text:
                post_text_to_process = forwarded_text
                image_to_show = uploaded_image
                trigger_process = True

    if trigger_process and post_text_to_process:
        st.write("---")
        final_clean_text, orig_p, new_p = process_post_pricing_dynamic(post_text_to_process, price_inc_rate, box_items_count)
        piece_p = round(new_p / box_items_count, 1) if isinstance(new_p, int) else "غير معروف"
        
        if image_to_show: st.image(image_to_show, caption="📸 صورة المنتج الأصلية", use_container_width=True)
        st.success(f"💵 السعر القديم: {orig_p} ج | السعر المحدث الجديد: {new_p} ج")
        
        st.subheader("📋 البوست الاحترافي المحدث لجمهورك:")
        final_commercial_post = (
            f"{final_clean_text}\n\n"
            f"📌 (سعر القطعة داخل البوكس واصل عليك بـ {piece_p} ج بس! 🔥)\n\n"
            f"🎁 **خصم خاص للكميات وأصحاب المحلات!** 💣🔥\n\n"
            f"🔗 للتواصل وطلب المنتج كاش فوراً: {fb_profile_link}"
        )
        st.text_area("اضغط هنا وانسخ البوست النهائي الجاهز للزق:", value=final_commercial_post, height=250)
