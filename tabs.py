import os
import re
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips as concat_videoclips
import moviepy.video.fx as vfx
import yt_dlp

import config
import utils

def render_tab_video(chosen_size, logo_position_choice, logo_offset_x, logo_offset_y, logo_opacity, logo_custom_w, logo_custom_h, audio_mode, uploaded_custom_audio):
    st.subheader("🚀 منصة تسريع، تقطيع ومونتاج الفيديو الذكي")
    option = st.radio("إدخال الفيديو:", ("لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)", "رفع ملف فيديو مباشر من جهازك"), key="vid_option_main")
    input_path = "web_input.mp4"
    output_path = "Bo0sViDClone_web_output.mp4"
    ready_to_process = False

    enable_trim = st.checkbox("تفعيل قص جزء محدد من الفيديو", key="enable_trim_key")
    c_t1, c_t2 = st.columns(2)
    with c_t1: trim_start = st.number_input("بداية القص (بالثواني):", min_value=0, value=0, key="t_start")
    with c_t2: trim_end = st.number_input("نهاية القص (بالثواني - 0 للكل):", min_value=0, value=0, key="t_end")

    speed_mode = st.radio("طريقة معالجة مدة الفيديو:", ["تسريع / تبطيء يدوي", "مُطابقة تلقائية مع مدة مستهدفة (Smart Speed-up)"], key="sp_mode")
    if speed_mode == "تسريع / تبطيء يدوي":
        manual_speed_factor = st.slider("مُعامل السرعة:", 0.5, 4.0, 1.0, key="sp_factor")
    else:
        target_video_duration_sec = st.slider("المدة النهائية المستهدفة (بالثواني):", 5, 120, 15, key="t_dur_sec")

    if option == "لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)":
        url = st.text_input("ضع الرابط:", placeholder="https://...", key="v_url_box")
        if url and re.match(r'http[s]?://', url):
            if st.button("🚀 ابدأ معالجة وتقطيع الفيديو", key="btn_proc_url"):
                with st.spinner("جاري السحب..."):
                    try:
                        if os.path.exists(input_path): os.remove(input_path)
                        ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': input_path, 'quiet': True, 'nocheckcertificate': True}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
                        ready_to_process = True
                    except Exception as e: st.error(f"خطأ: {str(e)}")
    else:
        uploaded_file = st.file_uploader("اسحب الفيديو هنا", type=["mp4", "mov", "avi"], key="v_file_up")
        if uploaded_file is not None and st.button("⚙️ ابدأ معالجة وتقطيع الفيديو", key="btn_proc_file"):
            with st.spinner("جاري التهيئة..."):
                if os.path.exists(input_path): os.remove(input_path)
                with open(input_path, "wb") as f: f.write(uploaded_file.read())
                ready_to_process = True

    if ready_to_process:
        with st.spinner("⚡ جاري المونتاج والرندرة..."):
            try:
                clip = VideoFileClip(input_path)
                if enable_trim:
                    end_val = clip.duration if trim_end <= 0 or trim_end > clip.duration else trim_end
                    clip = clip.subclip(min(trim_start, clip.duration - 1), end_val)

                if speed_mode == "مُطابقة تلقائية مع مدة مستهدفة (Smart Speed-up)":
                    calc_spd = clip.duration / float(target_video_duration_sec)
                    if calc_spd > 0: clip = clip.fx(vfx.speedx, calc_spd)
                else:
                    if manual_speed_factor != 1.0: clip = clip.fx(vfx.speedx, manual_speed_factor)

                if chosen_size: clip = clip.fx(vfx.resize, width=chosen_size[0], height=chosen_size[1])
                
                modified_clip = clip.fx(vfx.colorx, 1.05)
                
                if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" and uploaded_custom_audio is not None:
                    t_aud = os.path.join(config.TMP_DIR, "custom_audio.mp3")
                    with open(t_aud, "wb") as f: f.write(uploaded_custom_audio.read())
                    audio_overlay = AudioFileClip(t_aud).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                elif os.path.exists(config.CUSTOM_AUDIO_TRACK):
                    audio_overlay = AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, modified_clip.duration)
                    modified_clip = modified_clip.set_audio(audio_overlay)
                
                if utils.ensure_valid_image(config.ACTIVE_LOGO_PATH):
                    vx, vy = utils.calculate_exact_position(modified_clip.w, modified_clip.h, logo_custom_w, logo_custom_h, logo_position_choice, logo_offset_x, logo_offset_y)
                    logo = (ImageClip(config.ACTIVE_LOGO_PATH)
                            .set_duration(modified_clip.duration)
                            .resize(newsize=(logo_custom_w, logo_custom_h))
                            .set_pos((vx, vy))
                            .set_opacity(logo_opacity))
                    final_clip = CompositeVideoClip([modified_clip, logo])
                else:
                    final_clip = modified_clip
                
                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
                clip.close()
                final_clip.close()
                st.success("🎉 تم المونتاج بنجاح!")
                st.video(output_path)
            except Exception as e: st.error(f"خطأ: {str(e)}")

def render_tab_images(blur_bg_opt, blur_intensity_val, logo_opacity, fit_auto_logo, logo_custom_w, logo_custom_h, brand_text_scale, brand_color, brand_position_choice, brand_offset_x, brand_offset_y, extra_brand_suffix, extra_text_scale, extra_color, extra_position_choice, extra_offset_x, extra_offset_y, chosen_size, enhance_quality_opt, sharpness_slider_val, quality_slider_val, logo_position_choice, logo_offset_x, logo_offset_y, color_preset, enable_crop_opt, crop_l, crop_t, crop_r, crop_b, total_target_video_duration, image_duration_per_slide, audio_mode, uploaded_custom_audio, font_choice):
    st.subheader("🖼️ مصنع تجميل صور المنتجات وفيديوهات السلايد شو الذكية")
    uploaded_images = st.file_uploader("ارفع الصور:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="img_up_tab2")
    show_orig_toggle = st.checkbox("👁️ عرض الصور الأصلية", key="show_orig_tab2")

    if uploaded_images:
        album_choice = "📥 ألبوم صور مفرودة منفصلة" if len(uploaded_images) == 1 else st.radio("اختر نمط التصدير:", ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"), key="alb_choice_tab2")

        if show_orig_toggle:
            for idx, img_f in enumerate(uploaded_images):
                st.image(img_f, caption=f"أصل صورة {idx+1}", use_container_width=True)
        else:
            if st.button("⚙️ ابدأ معالجة الصور", key="btn_proc_imgs"):
                saved_paths = []
                for i, img_file in enumerate(uploaded_images):
                    temp_p = f"temp_prod_{i}.png"
                    with open(temp_p, "wb") as f: f.write(img_file.read())
                    
                    processed_p = utils.process_image_template(
                        temp_p, blur_background=blur_bg_opt, blur_intensity=blur_intensity_val, opacity_val=logo_opacity,
                        fit_auto_logo=fit_auto_logo, logo_custom_w=logo_custom_w, logo_custom_h=logo_custom_h,
                        brand_text_scale=brand_text_scale, brand_color=brand_color, brand_pos=brand_position_choice,
                        brand_off_x=brand_offset_x, brand_off_y=brand_offset_y, extra_text=extra_brand_suffix,
                        extra_text_scale=extra_text_scale, extra_color=extra_color, extra_pos=extra_position_choice,
                        extra_off_x=extra_offset_x, extra_off_y=extra_offset_y, target_size=chosen_size,
                        enhance_quality=enhance_quality_opt, sharpness_val=sharpness_slider_val, quality_val=quality_slider_val,
                        logo_pos_mode=logo_position_choice, logo_off_x=logo_offset_x, logo_off_y=logo_offset_y,
                        color_preset=color_preset, enable_crop=enable_crop_opt, c_left=crop_l, c_top=crop_t, c_right=crop_r, c_bottom=crop_b,
                        font_choice=font_choice
                    )
                    saved_paths.append(processed_p)
                    if os.path.exists(temp_p): os.remove(temp_p)
                
                if album_choice == "📥 ألبوم صور مفرودة منفصلة":
                    st.success("🎉 تمت المعالجة بنجاح!")
                    for idx, p in enumerate(saved_paths): st.image(p, caption=f"منتج {idx+1}", use_container_width=True)
                elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
                    collage_result = utils.create_image_collage(saved_paths, chosen_size if chosen_size else (1080, 1080))
                    st.image(collage_result, caption="صورة الكولاج", use_container_width=True)
                else:
                    dur = total_target_video_duration / len(saved_paths) if total_target_video_duration else image_duration_per_slide
                    with st.spinner("🎬 جاري رندرة السلايد شو..."):
                        img_clips = [ImageClip(p).set_duration(dur) for p in saved_paths]
                        v_slide = concat_videoclips(img_clips, method="compose")
                        v_slide_path = "slideshow_out.mp4"
                        v_slide.write_videofile(v_slide_path, codec="libx264", fps=24, preset="ultrafast")
                        st.video(v_slide_path)

def render_tab_radar(current_channels):
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير الذكي ونشر تليجرام")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر (%):", min_value=0, max_value=100, value=config.DEFAULT_PRICE_INC_RATE, key="p_rate")
    with col2: box_items_count = st.number_input("عدد القطع بالعلبة:", min_value=1, max_value=100, value=config.DEFAULT_BOX_ITEMS_COUNT, key="b_items")
    fb_link = st.text_input("رابط صفحتك للتواصل:", value="https://www.facebook.com/montgk1", key="fb_url")
    max_price = st.number_input("الحد الأقصى للسعر:", min_value=1, max_value=9999999, value=5000, key="max_p")
    date_filter = st.radio("النطاق الزمني:", ("اليوم فقط", "الأمس واليوم", "قبل أمس والـ 3 أيام الأخيرة", "كل البوستات المتاحة للقناة"), index=3, horizontal=True, key="d_filt")
    
    radar_mode = st.radio("مصدر المحتوى:", ("🛰️ سحب رادار حي وفوري", "📋 إدخل يدوي لبوست معموله Forward"), key="r_mode")
    if "cached_posts" not in st.session_state: st.session_state["cached_posts"] = []

    if radar_mode == "🛰️ سحب رادار حي وفوري":
        target_ch = st.selectbox("اختر القناة:", current_channels, key="sel_ch")
        if st.button("🛰️ قنص المحتوى", key="btn_fetch"):
            with st.spinner("جاري السحب والتحليل الذكي..."):
                try:
                    res = requests.get(f"https://t.me/s/{target_ch}", headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
                    if res.status_code == 200:
                        soup = BeautifulSoup(res.content, "html.parser")
                        messages = soup.find_all("div", class_=lambda x: x and 'tgme_widget_message_wrap' in x)
                        temp_collected = []
                        for msg in reversed(messages):
                            text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                            if text_div:
                                p_text = text_div.text.strip()
                                photo_url = None
                                photo_tag = msg.find("a", {"class": "tgme_widget_message_photo_wrap"})
                                if photo_tag:
                                    m = re.search(r"url\(['\"]?(.*?)['\"]?\)", photo_tag.get("style", ""))
                                    if m: photo_url = 'https:' + m.group(1) if m.group(1).startswith('//') else m.group(1)
                                auto_price, old_str = utils.extract_original_price_only(p_text, max_limit=max_price)
                                temp_collected.append({"text": p_text, "image": photo_url, "auto_price": auto_price, "old_str": old_str})
                        st.session_state["cached_posts"] = temp_collected
                        st.success(f"🎯 تم قنص وتحليل {len(temp_collected)} بوست بذكاء!")
                except Exception as e: st.error(f"خطأ: {str(e)}")
    else:
        fwd_text = st.text_area("نص البوست:", key="fwd_t")
        fwd_img = st.file_uploader("الصورة:", key="fwd_img")
        if st.button("⚡ تحليل وتعديل فوراً", key="btn_man"):
            if fwd_text:
                auto_price, old_str = utils.extract_original_price_only(fwd_text, max_limit=max_price)
                st.session_state["cached_posts"] = [{"text": fwd_text, "image": fwd_img, "auto_price": auto_price, "old_str": old_str}]

    if st.session_state["cached_posts"]:
        for idx, item in enumerate(st.session_state["cached_posts"]):
            st.markdown(f"#### 📦 منتج رقم {idx + 1}")
            if item["image"]: st.image(item["image"], width=250)
            orig_p = st.number_input(f"السعر الأصلي المكتشف {idx+1}:", min_value=0, value=int(item["auto_price"]), key=f"orig_p_{idx}")
            new_p = int(orig_p * (1 + (price_inc_rate / 100)))
            
            # --- حاسبة الأرباح الذكية الفورية ---
            profit_margin = new_p - orig_p
            st.success(f"💵 **حاسبة الأرباح الذكية:** المكسب المتوقع في القطعة الواحدة = **{profit_margin} جنيه** (بنسبة زيادة {price_inc_rate}%)")
            
            smart_desc = utils.generate_smart_ai_description(item["text"])
            auto_tags = utils.generate_auto_hashtags(item["text"][:15])
            
            st.info("💡 **الوصف الذكي المقترح بواسطة النظام:**")
            st.caption(smart_desc)
            
            apply_smart = st.checkbox(f"🔄 اعتماد الوصف الذكي لمنتج {idx+1}؟", value=False, key=f"ai_chk_{idx}")
            
            if apply_smart:
                final_post = f"{smart_desc}\n\n📌 سعر العرض الجديد: {new_p} ج\n🔗 للتواصل: {fb_link}\n\n{auto_tags}"
            else:
                clean_t = re.sub(r'#\w+|http[s]?://\S+', '', item["text"])
                final_desc = clean_t.replace(item["old_str"], str(new_p), 1) if item["old_str"] and item["old_str"] in clean_t else clean_t + f"\nالسعر: {new_p} ج"
                final_post = f"{final_desc}\n\n📌 سعر العرض الجديد: {new_p} ج\n🔗 للتواصل: {fb_link}"
            
            post_content = st.text_area(f"البوست النهائي {idx+1}:", value=final_post, height=150, key=f"post_txt_{idx}")
            
            pub_col1, pub_col2 = st.columns([2, 1])
            with pub_col1: pub_ch = st.text_input(f"قناة النشر #{idx+1}:", value=current_channels[0], key=f"p_ch_{idx}")
            with pub_col2:
                st.write("")
                st.write("")
                if st.button(f"🚀 نشر #{idx+1}", key=f"btn_pub_{idx}"):
                    img_s = item["image"] if isinstance(item["image"], str) else None
                    ok, msg = utils.send_telegram_post(config.TELEGRAM_BOT_TOKEN, pub_ch, post_content, img_s)
                    if ok: st.success(msg)
                    else: st.error(msg)
            st.markdown("---")

def render_tab_trends():
    st.subheader("🔍 رادار المنتجات الأكثر بحثاً في مصر")
    cat = st.selectbox("اختر المجال:", ["الكل", "أزياء وموضة", "إلكترونيات"], key="trend_cat")
    trends = {"الكل": {"products": ["ساعات سمارت", "ماكينات حلاقة", "سماعات ايربودز"], "hashtags": ["#عروض_مصر", "#تريند"]},
              "أزياء وموضة": {"products": ["ملابس صيفية", "أحذية رياضية"], "hashtags": ["#موضة", "#أزياء"]},
              "إلكترونيات": {"products": ["باور بانك", "ستاند تصوير"], "hashtags": ["#إلكترونيات"]}}
    data = trends.get(cat, trends["الكل"])
    
    c1, c2 = st.columns(2)
    with c1:
        sel_prod = st.radio("المنتج:", data["products"], key="r_prod")
        st.info(" ".join(data["hashtags"]))
    with c2:
        user_body = st.text_area("تفاصيل العرض:", value="خصم حصري لفترة محدودة والتوصيل لأي مكان.", height=120, key="u_body")
        if st.button("🚀 توليد اسطمبة البوست الذكية", key="btn_tpl"):
            st.code(f"🔥 عرض خاص على {sel_prod}!\n\n{user_body}\n\n{' '.join(data['hashtags'])}", language="markdown")
