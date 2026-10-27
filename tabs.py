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


def render_tab_images(blur_bg_opt, blur_intensity_val, logo_opacity, fit_auto_logo, logo_custom_w, logo_custom_h, brand_text_scale, brand_color, brand_position_choice, brand_offset_x, brand_offset_y, extra_brand_suffix, extra_text_scale, extra_color, extra_position_choice, extra_offset_x, extra_offset_y, chosen_size, enhance_quality_opt, sharpness_slider_val, quality_slider_val, logo_position_choice, logo_offset_x, logo_offset_y, color_preset, enable_crop_opt, crop_l, crop_t, crop_r, crop_b, total_target_video_duration, image_duration_per_slide, audio_mode, uploaded_custom_audio, font_choice, remove_logo_bg=True, smart_logo_position=False):
    st.subheader("🖼️ مصنع تجميل صور المنتجات وفيديوهات السلايد شو الذكية")
    uploaded_images = st.file_uploader("ارفع الصور:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="img_up_tab2")
    show_orig_toggle = st.checkbox("👁️ عرض الصور الأصلية", key="show_orig_tab2")
    st.info("✂️ القص اليدوي موجود في الشريط الجانبي: فعّل Crop وحدد القص من كل اتجاه قبل بدء المعالجة.")
    if not uploaded_images: return

    st.markdown("### 📣 إعلان المنتج من الصورة")
    st.caption("اكتب تفاصيل أو اسطمبة اختيارية. عند توفر OPENAI_API_KEY سيقرأ النظام الصورة ويكتب إعلانًا عربيًا تلقائيًا؛ وبدونه سيستخدم القالب المحلي بدل توقف التطبيق.")
    ad_details = st.text_input("اسم المنتج أو تفاصيله:", key="ad_details")
    ad_template = st.text_area("اسطمبة الإعلان اليدوية (اختياري):", placeholder="مثال: {المنتج} — جودة عالية، اطلب الآن...", key="ad_template")
    ad_col1, ad_col2 = st.columns(2)
    with ad_col1:
        if st.button("🔥 جلب هاشتاجات اليوم", key="fetch_trending_tags"):
            st.session_state.trending_hashtags = utils.get_trending_hashtags()
    with ad_col2:
        if st.button("🤖 اقرأ الصورة واكتب إعلان", key="generate_image_ad"):
            tags = st.session_state.get("trending_hashtags") or utils.get_trending_hashtags()
            generated, vision_used = utils.generate_product_ad(uploaded_images[0].getvalue(), ad_template, ad_details, tags)
            st.session_state.generated_ad_text = generated
            st.session_state.generated_ad_vision = vision_used
    if "generated_ad_text" not in st.session_state:
        st.session_state.generated_ad_text = ""
    if st.session_state.generated_ad_text:
        if not st.session_state.get("generated_ad_vision", False):
            st.warning("تم استخدام القالب المحلي. للقراءة الفعلية لتفاصيل الصورة أضف OPENAI_API_KEY في Secrets الخاصة بـ Streamlit.")
        st.text_area("البوست الإعلاني الجاهز للتعديل والنسخ:", key="generated_ad_text", height=220)
    if st.session_state.get("trending_hashtags"):
        st.caption("هاشتاجات اليوم: " + " ".join(st.session_state.trending_hashtags))
    album_choice = "📥 ألبوم صور مفرودة منفصلة" if len(uploaded_images) == 1 else st.radio("اختر نمط التصدير:", ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"), key="alb_choice_tab2")
    if show_orig_toggle:
        for idx, img_file in enumerate(uploaded_images): st.image(img_file, caption=f"أصل صورة {idx + 1}", use_container_width=True)
        return
    if not st.button("⚙️ ابدأ معالجة الصور", key="btn_proc_imgs"): return
    saved_paths = []
    for index, img_file in enumerate(uploaded_images):
        temp_path = os.path.join(config.TMP_DIR, f"temp_prod_{index}.png")
        with open(temp_path, "wb") as stream: stream.write(img_file.getvalue())
        saved_paths.append(utils.process_image_template(temp_path, blur_background=blur_bg_opt, blur_intensity=blur_intensity_val, opacity_val=logo_opacity, fit_auto_logo=fit_auto_logo, logo_custom_w=logo_custom_w, logo_custom_h=logo_custom_h, brand_text_scale=brand_text_scale, brand_color=brand_color, brand_pos=brand_position_choice, brand_off_x=brand_offset_x, brand_off_y=brand_offset_y, extra_text=extra_brand_suffix, extra_text_scale=extra_text_scale, extra_color=extra_color, extra_pos=extra_position_choice, extra_off_x=extra_offset_x, extra_off_y=extra_offset_y, target_size=chosen_size, enhance_quality=enhance_quality_opt, sharpness_val=sharpness_slider_val, quality_val=quality_slider_val, logo_pos_mode=logo_position_choice, logo_off_x=logo_offset_x, logo_off_y=logo_offset_y, color_preset=color_preset, enable_crop=enable_crop_opt, c_left=crop_l, c_top=crop_t, c_right=crop_r, c_bottom=crop_b, font_choice=font_choice, remove_logo_bg=remove_logo_bg, smart_logo_position=smart_logo_position))
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
    st.subheader("🛰️ رادار المنتجات اليدوي وكتالوج التصدير")
    st.caption("لا توجد متابعة في الخلفية: اضغط تشغيل الرادار لسحب دفعة واحدة من القنوات العامة، ثم راجع المنتجات قبل الاعتماد.")

    col1, col2, col3 = st.columns(3)
    with col1:
        profit_percent = st.number_input("نسبة الربح (%)", min_value=0.0, max_value=300.0, value=35.0, step=1.0, key="radar_profit")
    with col2:
        max_messages = st.number_input("أقصى عدد رسائل", min_value=1, max_value=500, value=50, step=10, key="radar_max_messages")
    with col3:
        max_price = st.number_input("أقصى سعر أصلي (0 = بلا حد)", min_value=0, max_value=9999999, value=0, step=50, key="radar_max_price")

    channels_text = st.text_area("القنوات العامة المراد فحصها", value="\n".join(current_channels), height=90, key="radar_channels_text", help="اكتب username كل قناة في سطر، مع أو بدون @")
    source_rule = st.radio("ابدأ السحب من:", ("آخر الرسائل المتاحة", "من تاريخ", "بعد رسالة تحتوي على نص"), horizontal=True, key="radar_source_rule")
    date_from = st.date_input("التاريخ من", value=__import__('datetime').date.today(), key="radar_date_from") if source_rule == "من تاريخ" else None
    marker_text = st.text_input("نص علامة البداية", placeholder="مثال: ابدأ من هنا", key="radar_marker_text") if source_rule == "بعد رسالة تحتوي على نص" else ""
    rounding = st.checkbox("تقريب السعر لأقرب 5 (2.5 أو أقل للأسفل، أكبر من 2.5 للأعلى)", value=True, key="radar_rounding")

    st.markdown("### بعد مراجعة المنتجات")
    review_required = st.checkbox("مراجعة يدوية لكل منتج قبل الاعتماد", value=True, key="radar_review_required")
    auto_publish_enabled = st.checkbox("السماح بالنشر التلقائي بعد الضغط على زر النشر", value=False, key="radar_auto_publish")
    publish_channel = st.text_input("قناة النشر الاختيارية", placeholder="@my_channel", key="radar_publish_channel")

    if "radar_products" not in st.session_state:
        st.session_state.radar_products = []

    if st.button("🛰️ تشغيل الرادار الآن", type="primary", key="radar_scan_now"):
        channels = [line.strip().lstrip('@') for line in channels_text.splitlines() if line.strip()]
        if not channels:
            st.error("أدخل قناة عامة واحدة على الأقل.")
        else:
            found = []
            with st.spinner("جاري فحص القنوات العامة مرة واحدة..."):
                try:
                    for channel in channels:
                        batch = utils.fetch_public_channel_messages(channel, date_from=date_from, marker_text=marker_text, max_messages=int(max_messages))
                        for item in batch:
                            if max_price and item.get('auto_price', 0) > max_price:
                                continue
                            found.append(utils.build_catalog_product(item, profit_percent, rounding))
                    # Remove duplicates while preserving source order.
                    unique = {}
                    for product in found:
                        unique[product['id']] = product
                    st.session_state.radar_products = list(unique.values())
                    st.success(f"تم العثور على {len(st.session_state.radar_products)} منتجًا. راجعها قبل التصدير أو النشر.")
                except Exception as exc:
                    st.error(f"تعذر فحص القنوات: {exc}")

    products = st.session_state.get("radar_products", [])
    if not products:
        st.info("لم يتم تحميل منتجات بعد. اكتب القنوات وحدد البداية ثم اضغط تشغيل الرادار.")
        return

    st.markdown(f"### المنتجات المكتشفة ({len(products)})")
    if st.button("✅ تحديد كل المنتجات للمراجعة", key="radar_approve_all"):
        for idx in range(len(products)):
            products[idx]['approved'] = True
        st.rerun()

    for index, product in enumerate(products):
        with st.expander(f"📦 {index + 1}. {product.get('title', 'منتج جديد')} — {product.get('price', 0)} جنيه", expanded=index == 0):
            if product.get('image_link'):
                st.image(product['image_link'], width=220)
            product['title'] = st.text_input("اسم المنتج", value=product.get('title', ''), key=f"radar_title_{index}")
            product['description'] = st.text_area("الوصف والمقاسات والألوان والخامة", value=product.get('description', ''), height=120, key=f"radar_desc_{index}")
            price_col, source_col = st.columns(2)
            with price_col:
                product['price'] = st.number_input("سعر البيع بعد الربح", min_value=0, value=int(product.get('price') or 0), step=5, key=f"radar_price_{index}")
                st.caption(f"السعر الأصلي: {product.get('original_price', 0)} جنيه — ربح {product.get('profit_percent', 0):g}%")
            with source_col:
                st.caption(f"المصدر: @{product.get('source_channel', '')}")
                st.caption(f"التاريخ: {product.get('source_date', '') or 'غير متاح'}")
            if review_required:
                product['approved'] = st.checkbox("أوافق على اعتماد هذا المنتج", value=bool(product.get('approved')), key=f"radar_approved_{index}")
            else:
                product['approved'] = True

    approved = [product for product in products if product.get('approved')]
    st.divider()
    st.markdown(f"### المعتمد للتصدير: {len(approved)}")
    if approved:
        csv_bytes = utils.make_catalog_csv(approved)
        st.download_button("⬇️ تنزيل CSV لكتالوج Meta", data=csv_bytes, file_name="catalog_meta.csv", mime="text/csv", key="download_catalog_csv")
        st.download_button("⬇️ تنزيل ZIP بالكتالوج والصور", data=utils.make_catalog_zip(approved), file_name="catalog_products.zip", mime="application/zip", key="download_catalog_zip")
        if publish_channel:
            if not auto_publish_enabled:
                st.warning("فعّل خيار السماح بالنشر التلقائي إذا أردت زر النشر أن يرسل إلى القناة.")
            if st.button("🚀 نشر المنتجات المعتمدة على تيليجرام", key="radar_publish_approved"):
                if not auto_publish_enabled:
                    st.error("النشر متوقف للحماية. فعّل السماح بالنشر التلقائي أولًا.")
                else:
                    sent = 0
                    for product in approved:
                        text = f"{product['title']}\n\n{product['description']}\n\n💵 السعر: {product['price']} ج\n\nMr :- Bo0"
                        ok, _message = utils.send_telegram_post(config.TELEGRAM_BOT_TOKEN, publish_channel, text, product.get('image_link'))
                        sent += int(ok)
                    st.success(f"تم إرسال {sent} من {len(approved)} منتجًا إلى {publish_channel}.")
    else:
        st.info("حدد المنتجات التي تريد اعتمادها يدويًا، ثم سيظهر التصدير والنشر هنا.")

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
