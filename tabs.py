import os
import re
import requests
import streamlit as st
from bs4 import BeautifulSoup
from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip, concatenate_videoclips as concat_videoclips
import moviepy.video.fx.all as vfx
import yt_dlp

import config
import utils


def render_tab_video(chosen_size, logo_position_choice, logo_offset_x, logo_offset_y, logo_opacity, logo_custom_w, logo_custom_h, audio_mode, uploaded_custom_audio):
    st.subheader("🚀 منصة تسريع، تقطيع ومونتاج الفيديو الذكي")
    option = st.radio("إدخال الفيديو:", ("لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)", "رفع ملف فيديو مباشر من جهازك"), key="vid_option_main")
    input_path, output_path = "web_input.mp4", "Bo0sViDClone_web_output.mp4"
    ready_to_process = False
    enable_trim = st.checkbox("تفعيل قص جزء محدد من الفيديو", key="enable_trim_key")
    c_t1, c_t2 = st.columns(2)
    with c_t1: trim_start = st.number_input("بداية القص (بالثواني):", min_value=0, key="t_start")
    with c_t2: trim_end = st.number_input("نهاية القص (بالثواني - 0 للكل):", min_value=0, key="t_end")
    speed_mode = st.radio("طريقة معالجة مدة الفيديو:", ["تسريع / تبطيء يدوي", "مُطابقة تلقائية مع مدة مستهدفة (Smart Speed-up)"], key="sp_mode")
    if speed_mode == "تسريع / تبطيء يدوي":
        manual_speed_factor = st.slider("مُعامل السرعة:", 0.5, 4.0, key="sp_factor")
    else:
        target_video_duration_sec = st.slider("المدة النهائية المستهدفة (بالثواني):", 5, 120, key="t_dur_sec")
    if option == "لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)":
        url = st.text_input("ضع الرابط:", placeholder="https://...", key="v_url_box")
        if url and re.match(r"http[s]?://", url) and st.button("🚀 ابدأ معالجة وتقطيع الفيديو", key="btn_proc_url"):
            with st.spinner("جاري السحب..."):
                try:
                    if os.path.exists(input_path): os.remove(input_path)
                    with yt_dlp.YoutubeDL({'format': 'best[ext=mp4]/best', 'outtmpl': input_path, 'quiet': True, 'nocheckcertificate': True}) as ydl: ydl.download([url])
                    ready_to_process = True
                except Exception as exc: st.error(f"خطأ: {exc}")
    else:
        uploaded_file = st.file_uploader("اسحب الفيديو هنا", type=["mp4", "mov", "avi"], key="v_file_up")
        if uploaded_file is not None and st.button("⚙️ ابدأ معالجة وتقطيع الفيديو", key="btn_proc_file"):
            with open(input_path, "wb") as stream: stream.write(uploaded_file.getvalue())
            ready_to_process = True
    if not ready_to_process:
        return
    with st.spinner("⚡ جاري المونتاج والرندرة..."):
        try:
            clip = VideoFileClip(input_path)
            if enable_trim:
                end_val = clip.duration if trim_end <= 0 or trim_end > clip.duration else trim_end
                clip = clip.subclip(min(trim_start, max(0, clip.duration - 1)), end_val)
            if speed_mode == "مُطابقة تلقائية مع مدة مستهدفة (Smart Speed-up)":
                clip = clip.fx(vfx.speedx, clip.duration / float(target_video_duration_sec))
            elif manual_speed_factor != 1.0:
                clip = clip.fx(vfx.speedx, manual_speed_factor)
            if chosen_size: clip = clip.fx(vfx.resize, width=chosen_size[0], height=chosen_size[1])
            modified_clip = clip.fx(vfx.colorx, 1.05)
            if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" and uploaded_custom_audio is not None:
                audio_path = os.path.join(config.TMP_DIR, "custom_audio.mp3")
                with open(audio_path, "wb") as stream: stream.write(uploaded_custom_audio.getvalue())
                modified_clip = modified_clip.set_audio(AudioFileClip(audio_path).subclip(0, modified_clip.duration))
            elif os.path.exists(config.CUSTOM_AUDIO_TRACK):
                modified_clip = modified_clip.set_audio(AudioFileClip(config.CUSTOM_AUDIO_TRACK).subclip(0, modified_clip.duration))
            if utils.ensure_valid_image(config.ACTIVE_LOGO_PATH):
                vx, vy = utils.calculate_exact_position(modified_clip.w, modified_clip.h, logo_custom_w, logo_custom_h, logo_position_choice, logo_offset_x, logo_offset_y)
                logo = ImageClip(config.ACTIVE_LOGO_PATH).set_duration(modified_clip.duration).resize(newsize=(logo_custom_w, logo_custom_h)).set_pos((vx, vy)).set_opacity(logo_opacity)
                final_clip = CompositeVideoClip([modified_clip, logo])
            else: final_clip = modified_clip
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
            clip.close(); final_clip.close()
            st.success("🎉 تم المونتاج بنجاح!")
            st.video(output_path)
        except Exception as exc: st.error(f"خطأ: {exc}")


def render_tab_images(blur_bg_opt, blur_intensity_val, logo_opacity, fit_auto_logo, logo_custom_w, logo_custom_h, brand_text_scale, brand_color, brand_position_choice, brand_offset_x, brand_offset_y, extra_brand_suffix, extra_text_scale, extra_color, extra_position_choice, extra_offset_x, extra_offset_y, chosen_size, enhance_quality_opt, sharpness_slider_val, quality_slider_val, logo_position_choice, logo_offset_x, logo_offset_y, color_preset, enable_crop_opt, crop_l, crop_t, crop_r, crop_b, total_target_video_duration, image_duration_per_slide, audio_mode, uploaded_custom_audio, font_choice, remove_logo_bg=True):
    st.subheader("🖼️ مصنع تجميل صور المنتجات وفيديوهات السلايد شو الذكية")
    uploaded_images = st.file_uploader("ارفع الصور:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="img_up_tab2")
    show_orig_toggle = st.checkbox("👁️ عرض الصور الأصلية", key="show_orig_tab2")
    if not uploaded_images: return
    album_choice = "📥 ألبوم صور مفرودة منفصلة" if len(uploaded_images) == 1 else st.radio("اختر نمط التصدير:", ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"), key="alb_choice_tab2")
    if show_orig_toggle:
        for idx, img_file in enumerate(uploaded_images): st.image(img_file, caption=f"أصل صورة {idx + 1}", use_container_width=True)
        return
    if not st.button("⚙️ ابدأ معالجة الصور", key="btn_proc_imgs"): return
    saved_paths = []
    for index, img_file in enumerate(uploaded_images):
        temp_path = os.path.join(config.TMP_DIR, f"temp_prod_{index}.png")
        with open(temp_path, "wb") as stream: stream.write(img_file.getvalue())
        saved_paths.append(utils.process_image_template(temp_path, blur_background=blur_bg_opt, blur_intensity=blur_intensity_val, opacity_val=logo_opacity, fit_auto_logo=fit_auto_logo, logo_custom_w=logo_custom_w, logo_custom_h=logo_custom_h, brand_text_scale=brand_text_scale, brand_color=brand_color, brand_pos=brand_position_choice, brand_off_x=brand_offset_x, brand_off_y=brand_offset_y, extra_text=extra_brand_suffix, extra_text_scale=extra_text_scale, extra_color=extra_color, extra_pos=extra_position_choice, extra_off_x=extra_offset_x, extra_off_y=extra_offset_y, target_size=chosen_size, enhance_quality=enhance_quality_opt, sharpness_val=sharpness_slider_val, quality_val=quality_slider_val, logo_pos_mode=logo_position_choice, logo_off_x=logo_offset_x, logo_off_y=logo_offset_y, color_preset=color_preset, enable_crop=enable_crop_opt, c_left=crop_l, c_top=crop_t, c_right=crop_r, c_bottom=crop_b, font_choice=font_choice, remove_logo_bg=remove_logo_bg))
        if os.path.exists(temp_path): os.remove(temp_path)
    if album_choice == "📥 ألبوم صور مفرودة منفصلة":
        st.success("🎉 تمت المعالجة بنجاح!")
        for idx, path in enumerate(saved_paths): st.image(path, caption=f"منتج {idx + 1}", use_container_width=True)
    elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
        st.image(utils.create_image_collage(saved_paths, chosen_size or (1080, 1080)), caption="صورة الكولاج", use_container_width=True)
    else:
        duration = total_target_video_duration / len(saved_paths) if total_target_video_duration else image_duration_per_slide
        with st.spinner("🎬 جاري رندرة السلايد شو..."):
            clips = [ImageClip(path).set_duration(duration) for path in saved_paths]
            video = concat_videoclips(clips, method="compose")
            video.write_videofile("slideshow_out.mp4", codec="libx264", fps=24, preset="ultrafast")
            st.video("slideshow_out.mp4")


def render_tab_radar(current_channels):
    st.subheader("🛰️ مركز الفحص والـ Forward وإعادة التسعير الذكي ونشر تليجرام")
    st.caption("اسحب من قناة، ثم اسحب قناة أخرى؛ عند تطابق المنتج سيظهر السعر الأرخص مع checkbox للموافقة قبل النشر.")
    col1, col2 = st.columns(2)
    with col1: price_inc_rate = st.number_input("نسبة زيادة السعر (%):", min_value=0, max_value=100, key="p_rate")
    with col2: st.number_input("عدد القطع بالعلبة:", min_value=1, max_value=100, key="b_items")
    fb_link = st.text_input("رابط صفحتك للتواصل:", key="fb_url")
    max_price = st.number_input("الحد الأقصى للسعر:", min_value=1, max_value=9999999, key="max_p")
    st.radio("النطاق الزمني:", ("اليوم فقط", "الأمس واليوم", "قبل أمس والـ 3 أيام الأخيرة", "كل البوستات المتاحة للقناة"), horizontal=True, key="d_filt")
    radar_mode = st.radio("مصدر المحتوى:", ("🛰️ سحب رادار حي وفوري", "📋 إدخل يدوي لبوست معموله Forward"), key="r_mode")
    if "cached_posts" not in st.session_state: st.session_state.cached_posts = []
    if radar_mode == "🛰️ سحب رادار حي وفوري":
        target_ch = st.selectbox("اختر القناة:", current_channels, key="sel_ch")
        if st.button("🛰️ قنص المحتوى", key="btn_fetch"):
            try:
                res = requests.get(f"https://t.me/s/{target_ch}", headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
                soup = BeautifulSoup(res.content, "html.parser") if res.status_code == 200 else None
                collected = []
                for msg in reversed(soup.find_all("div", class_=lambda value: value and "tgme_widget_message_wrap" in value) if soup else []):
                    text_div = msg.find("div", {"class": "tgme_widget_message_text"})
                    if not text_div: continue
                    photo_url = None
                    photo_tag = msg.find("a", {"class": "tgme_widget_message_photo_wrap"})
                    if photo_tag:
                        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", photo_tag.get("style", ""))
                        if match: photo_url = "https:" + match.group(1) if match.group(1).startswith("//") else match.group(1)
                    price, old = utils.extract_original_price_only(text_div.text.strip(), max_limit=max_price)
                    collected.append({"text": text_div.text.strip(), "image": photo_url, "auto_price": price, "old_str": old})
                price_index = st.session_state.setdefault("product_price_index", {})
                st.session_state.cached_posts = utils.compare_products(collected, target_ch, price_index)
                st.success(f"🎯 تم قنص وتحليل {len(collected)} بوست بذكاء!")
            except Exception as exc: st.error(f"خطأ: {exc}")
    else:
        text = st.text_area("نص البوست:", key="fwd_t")
        image = st.file_uploader("الصورة:", key="fwd_img")
        if st.button("⚡ تحليل وتعديل فوراً", key="btn_man") and text:
            price, old = utils.extract_original_price_only(text, max_limit=max_price)
            price_index = st.session_state.setdefault("product_price_index", {})
            st.session_state.cached_posts = utils.compare_products([{"text": text, "image": image, "auto_price": price, "old_str": old}], "manual", price_index)
    for index, item in enumerate(st.session_state.cached_posts):
        st.markdown(f"#### 📦 منتج رقم {index + 1}")
        if item.get("image"): st.image(item["image"], width=250)
        original = st.number_input(f"السعر الأصلي المكتشف {index + 1}:", min_value=0, value=int(item.get("auto_price") or 0), key=f"orig_p_{index}")
        effective_price, code = int(original), item.get("source_code", utils.supplier_code(item.get("source_channel", "manual")))
        comparison = item.get("comparison")
        if comparison and comparison["type"] == "cheaper":
            st.warning(f"🔎 نفس المنتج عند {comparison['channel']} بسعر أقل: {comparison['price']} جنيه — الكود {comparison['code']}")
            if st.checkbox("اعتماد المورد الأرخص والسعر المقترح", key=f"approve_compare_{index}_{item.get('comparison_key', 'x')}"):
                effective_price, code = int(comparison["price"]), comparison["code"]
        elif comparison and comparison["type"] == "current_cheaper": st.success(f"✅ المنتج الحالي أرخص بسعر {comparison['price']} جنيه — الكود {code}")
        elif comparison and comparison["type"] == "same_price": st.info("ℹ️ المنتج بنفس السعر موجود سابقًا؛ لا تعِد نشره إلا بعد تعديل الوصف أو السعر.")
        new_price = int(effective_price * (1 + price_inc_rate / 100))
        st.success(f"💵 المكسب المتوقع: **{new_price - effective_price} جنيه**")
        smart = utils.generate_smart_ai_description(item["text"])
        st.caption(smart)
        use_smart = st.checkbox(f"🔄 اعتماد الوصف الذكي لمنتج {index + 1}؟", key=f"ai_chk_{index}")
        if use_smart:
            post = f"{smart}\n\n📌 سعر العرض الجديد: {new_price} ج\n🔖 كود المورد: {code}\n🔗 للتواصل: {fb_link}\n\n{utils.generate_auto_hashtags(item['text'][:15])}"
        else:
            clean = utils.clean_product_text(item["text"], item.get("source_channel"))
            desc = clean.replace(item.get("old_str", ""), str(new_price), 1) if item.get("old_str") and item["old_str"] in clean else clean + f"\nالسعر: {new_price} ج"
            post = f"{desc}\n\n📌 سعر العرض الجديد: {new_price} ج\n🔖 كود المورد: {code}\n🔗 للتواصل: {fb_link}"
        content = st.text_area(f"البوست النهائي {index + 1}:", value=post, height=150, key=f"post_txt_{index}")
        pub_col, button_col = st.columns([2, 1])
        with pub_col: channel = st.text_input(f"قناة النشر #{index + 1}:", value=current_channels[0], key=f"p_ch_{index}")
        with button_col:
            st.write(""); st.write("")
            if st.button(f"🚀 نشر #{index + 1}", key=f"btn_pub_{index}"):
                ok, message = utils.send_telegram_post(config.TELEGRAM_BOT_TOKEN, channel, content, item["image"] if isinstance(item.get("image"), str) else None)
                st.success(message) if ok else st.error(message)
        st.markdown("---")


def render_tab_trends():
    st.subheader("🔍 رادار المنتجات الأكثر بحثاً في مصر")
    categories = {"الكل": (["ساعات سمارت", "ماكينات حلاقة", "سماعات ايربودز"], ["#عروض_مصر", "#تريند"]), "أزياء وموضة": (["ملابس صيفية", "أحذية رياضية"], ["#موضة", "#أزياء"]), "إلكترونيات": (["باور بانك", "ستاند تصوير"], ["#إلكترونيات"])}
    category = st.selectbox("اختر المجال:", list(categories), key="trend_cat")
    products, hashtags = categories[category]
    col1, col2 = st.columns(2)
    with col1:
        product = st.radio("المنتج:", products, key="r_prod")
        st.info(" ".join(hashtags))
    with col2:
        body = st.text_area("تفاصيل العرض:", value="خصم حصري لفترة محدودة والتوصيل لأي مكان.", height=120, key="u_body")
        if st.button("🚀 توليد اسطمبة البوست الذكية", key="btn_tpl"):
            st.code(f"🔥 عرض خاص على {product}!\n\n{body}\n\n{' '.join(hashtags)}", language="markdown")
