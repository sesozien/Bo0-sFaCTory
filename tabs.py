import csv
import hashlib
import io
import os
import re
import shutil
import uuid
from urllib.parse import quote
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip, concatenate_videoclips as concat_videoclips
import moviepy.video.fx.all as vfx
import yt_dlp

import config
import utils
from image_text_tools import cleanup_text_from_image, extract_product_from_image, remove_text_from_image


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


def _catalog_categories():
    defaults = ["توك", "اكسسوار", "أدوات منزلية", "رفايع مطبخ", "مكياجات", "خردوات", "أدوات مدرسية", "بلاستيكات"]
    if "catalog_custom_categories" not in st.session_state:
        st.session_state.catalog_custom_categories = config.load_categories()
    custom = st.session_state.get("catalog_custom_categories", [])
    return list(dict.fromkeys(defaults + custom))


def _catalog_row_id(row, index):
    return str(row.get("id") or row.get("image_path") or f"row-{index}")


def _image_fingerprint(path):
    try:
        digest = hashlib.sha1()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, TypeError):
        return ""


def _clean_product_name(value):
    name = os.path.splitext(os.path.basename(str(value or "")))[0]
    name = re.sub(r"[_\-]+", " ", name)
    return re.sub(r"\s+", " ", name).strip(" .") or "منتج جديد"


def _catalog_duplicate(rows, name, category, skip_index=None):
    wanted = re.sub(r"\s+", " ", str(name or "")).strip().casefold()
    for index, row in enumerate(rows):
        if skip_index == index:
            continue
        current = re.sub(r"\s+", " ", str(row.get("name", ""))).strip().casefold()
        if wanted and current == wanted and str(row.get("type", "")) == str(category):
            return True
    return False


def _persist_catalog(rows):
    st.session_state.catalog_rows = rows
    return config.save_catalog(rows)


def render_catalog_panel(processed_images=None):
    st.markdown("## 🗂️ كتالوج المنتجات")
    st.caption("كل منتج له صف مستقل. اكتب البيانات واضغط حفظ الصف، وسيُحفظ فورًا.")
    if st.button("📚 تحميل آخر نسخة من الكتالوج", key="catalog_reload_from_file"):
        st.session_state.catalog_rows = config.load_catalog()
        st.success("تم تحميل آخر نسخة محفوظة من الكتالوج.")
        st.rerun()
    categories = _catalog_categories()
    with st.sidebar.expander("➕ إضافة تصنيف جديد", expanded=False):
        new_category = st.text_input("اسم التصنيف", key="catalog_new_category")
        if st.button("إضافة التصنيف", key="catalog_add_category"):
            clean = new_category.strip()
            if clean and clean not in categories:
                st.session_state.catalog_custom_categories.append(clean)
                config.save_categories(st.session_state.catalog_custom_categories)
                st.success("تمت إضافة التصنيف وحفظه")
                st.rerun()
    with st.sidebar.expander("🧹 أدوات تنظيف الكتالوج", expanded=False):
        st.caption("يمسح ملف الكتالوج والصور والتصنيفات المخصصة نهائيًا.")
        confirm_clear = st.checkbox("أؤكد مسح الكتالوج بالكامل", key="catalog_clear_confirm")
        if st.button("مسح الكتالوج بالكامل", key="catalog_clear_all"):
            if not confirm_clear:
                st.warning("فعّل التأكيد أولًا")
            else:
                config.clear_catalog_storage()
                st.session_state.catalog_rows = []
                st.session_state.catalog_custom_categories = []
                st.success("تم مسح الكتالوج والصور والتصنيفات")
                st.rerun()
    if "catalog_rows" not in st.session_state:
        st.session_state.catalog_rows = config.load_catalog()
    rows = st.session_state.catalog_rows
    migrated_fingerprints = False
    for index, row in enumerate(rows):
        row.setdefault("id", _catalog_row_id(row, index))
        if not row.get("image_fingerprint") and row.get("image_path") and os.path.exists(row["image_path"]):
            row["image_fingerprint"] = _image_fingerprint(row["image_path"])
            migrated_fingerprints = True
    if migrated_fingerprints:
        _persist_catalog(rows)
    if processed_images:
        existing_fingerprints = {str(row.get("image_fingerprint")) for row in rows if row.get("image_fingerprint")}
        changed = False
        for image_path in processed_images:
            fingerprint = _image_fingerprint(str(image_path))
            if fingerprint and fingerprint in existing_fingerprints:
                continue
            suffix = os.path.splitext(str(image_path))[1] or ".jpg"
            durable_path = os.path.join(config.CATALOG_IMAGES_DIR, f"product_{uuid.uuid4().hex[:10]}{suffix}")
            try:
                shutil.copyfile(str(image_path), durable_path)
            except OSError:
                durable_path = str(image_path)
            rows.append({"id": uuid.uuid4().hex, "approved": False, "image_path": durable_path, "image_fingerprint": fingerprint, "name": _clean_product_name(durable_path), "type": categories[0], "case_price": 0.0, "pack_count": 1, "unit_price": 0.0, "notes": ""})
            if fingerprint:
                existing_fingerprints.add(fingerprint)
            changed = True
        if changed:
            _persist_catalog(rows)
            st.success("✅ الصور المعدلة اتضافت للكتالوج تلقائيًا")
    with st.expander("➕ إضافة منتج يدوي للكتالوج", expanded=not bool(rows)):
        manual_image = st.file_uploader("صورة المنتج المعدلة", type=["jpg", "jpeg", "png"], key="catalog_manual_image")
        default_name = _clean_product_name(manual_image.name) if manual_image else ""
        upload_token = hashlib.sha1(manual_image.getvalue()).hexdigest() if manual_image else ""
        if st.session_state.get("catalog_manual_upload_token") != upload_token:
            st.session_state.catalog_manual_upload_token = upload_token
            st.session_state.pop("catalog_ai_draft", None)
            for key in ("catalog_manual_name", "catalog_manual_type", "catalog_manual_case", "catalog_manual_count", "catalog_manual_notes"):
                st.session_state.pop(key, None)
        if manual_image:
            ai_col, hint_col = st.columns([1, 2])
            with ai_col:
                extract_details = st.button("🤖 استخراج التفاصيل من الصورة", key="catalog_extract_details")
            with hint_col:
                st.caption("يملأ الاسم والتصنيف والأسعار والمقاسات والألوان تلقائيًا، ثم تراجعها قبل الحفظ.")
            if extract_details:
                with st.spinner("جاري قراءة الصورة واستخراج بيانات المنتج..."):
                    draft, extracted_ok, extraction_message = utils.extract_product_details_from_image(manual_image.getvalue(), manual_image.name, st.session_state.get("catalog_manual_notes", ""))
                if extracted_ok:
                    st.session_state.catalog_ai_draft = draft
                    st.success(extraction_message)
                    st.rerun()
                else:
                    st.warning(extraction_message)
        draft = st.session_state.get("catalog_ai_draft", {})
        suggested_type = str(draft.get("type") or "").strip()
        if suggested_type and suggested_type not in categories:
            st.caption(f"التصنيف المقروء: {suggested_type} — اختر أقرب تصنيف من القائمة أو أضفه من الشريط الجانبي.")
        initial_type = suggested_type if suggested_type in categories else categories[0]
        initial_notes = str(draft.get("notes") or "")
        st.session_state.setdefault("catalog_manual_name", str(draft.get("name") or default_name))
        st.session_state.setdefault("catalog_manual_type", initial_type)
        st.session_state.setdefault("catalog_manual_case", float(draft.get("case_price") or 0))
        st.session_state.setdefault("catalog_manual_count", max(1, int(draft.get("pack_count") or 1)))
        st.session_state.setdefault("catalog_manual_notes", initial_notes)
        with st.form("catalog_manual_form", clear_on_submit=False):
            manual_name = st.text_input("اسم المنتج", key="catalog_manual_name")
            manual_type = st.selectbox("النوع", categories, key="catalog_manual_type")
            manual_case = st.number_input("سعر الدستة", min_value=0.0, step=1.0, key="catalog_manual_case")
            manual_count = st.number_input("عدد العبوة", min_value=1, step=1, key="catalog_manual_count")
            st.caption(f"سعر القطعة المحسوب: {manual_case / max(1, manual_count):.2f} جنيه")
            manual_notes = st.text_area("الملاحظات / المقاسات / الألوان / الخامة", key="catalog_manual_notes")
            manual_approved = st.checkbox("اعتماد المنتج للمتجر", key="catalog_manual_approved")
            manual_submit = st.form_submit_button("💾 حفظ المنتج في الكتالوج")
        if manual_submit:
            if not manual_image:
                st.error("ارفع صورة المنتج أولًا")
            elif not manual_name.strip():
                st.error("اكتب اسم المنتج")
            elif _catalog_duplicate(rows, manual_name, manual_type):
                st.warning("هذا المنتج موجود بنفس الاسم والتصنيف، لم تتم إضافته مرة أخرى")
            else:
                suffix = os.path.splitext(manual_image.name)[1].lower() or ".png"
                image_path = os.path.join(config.CATALOG_IMAGES_DIR, f"product_{uuid.uuid4().hex[:10]}{suffix}")
                with open(image_path, "wb") as stream:
                    stream.write(manual_image.getvalue())
                rows.append({"id": uuid.uuid4().hex, "approved": bool(manual_approved), "image_path": image_path, "image_fingerprint": _image_fingerprint(image_path), "name": manual_name.strip(), "type": manual_type, "case_price": float(manual_case), "pack_count": int(manual_count), "unit_price": round(float(manual_case) / max(1, int(manual_count)), 2), "notes": manual_notes.strip()})
                if _persist_catalog(rows):
                    st.success("✅ تم حفظ المنتج فورًا في الكتالوج")
                    st.rerun()
                else:
                    st.error("تعذر حفظ الكتالوج")
    if not rows:
        st.info("لا توجد منتجات. أضف منتجًا يدويًا أو عالج صورة من الأعلى.")
        return
    st.markdown(f"### المنتجات الحالية: {len(rows)} | المعتمدة للمتجر: {sum(bool(row.get('approved')) for row in rows)}")
    st.caption("غيّر الخانات داخل الصف ثم اضغط حفظ الصف. الاعتماد محفوظ مع الصف نفسه.")
    for index, row in enumerate(list(rows)):
        row_id = _catalog_row_id(row, index)
        name_key = f"cat_name_{row_id}"
        type_key = f"cat_type_{row_id}"
        approved_key = f"cat_approved_{row_id}"
        case_key = f"cat_case_{row_id}"
        count_key = f"cat_count_{row_id}"
        notes_key = f"cat_notes_{row_id}"
        st.session_state.setdefault(name_key, str(row.get("name", "")))
        st.session_state.setdefault(type_key, row.get("type") if row.get("type") in categories else categories[0])
        st.session_state.setdefault(approved_key, bool(row.get("approved", False)))
        st.session_state.setdefault(case_key, float(row.get("case_price") or 0))
        st.session_state.setdefault(count_key, max(1, int(row.get("pack_count") or 1)))
        st.session_state.setdefault(notes_key, str(row.get("notes", "")))
        with st.container(border=True):
            if row.get("image_path") and os.path.exists(row["image_path"]):
                st.image(row["image_path"], width=160, caption=f"صورة المنتج {index + 1}")
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("اسم المنتج", key=name_key)
                category = st.selectbox("النوع", categories, key=type_key)
                approved = st.checkbox("✅ اعتماد المنتج للمتجر", key=approved_key)
            with c2:
                case_price = st.number_input("سعر الدستة", min_value=0.0, step=1.0, key=case_key)
                pack_count = st.number_input("عدد العبوة", min_value=1, step=1, key=count_key)
                st.metric("سعر القطعة", f"{case_price / max(1, pack_count):.2f} جنيه")
            notes = st.text_area("الملاحظات / المقاسات / الألوان / الخامة", key=notes_key)
            save_col, delete_col = st.columns(2)
            with save_col:
                save_row = st.button("💾 حفظ الصف الآن", key=f"cat_save_{row_id}")
            with delete_col:
                delete_row = st.button("🗑️ حذف هذا المنتج", key=f"cat_delete_{row_id}")
            if save_row:
                if not name.strip():
                    st.error("اكتب اسم المنتج قبل الحفظ")
                elif _catalog_duplicate(rows, name, category, skip_index=index):
                    st.warning("يوجد منتج آخر بنفس الاسم والتصنيف")
                else:
                    rows[index] = {**row, "name": name.strip(), "type": category, "approved": bool(approved), "case_price": float(case_price), "pack_count": int(pack_count), "unit_price": round(float(case_price) / max(1, int(pack_count)), 2), "notes": notes.strip()}
                    _persist_catalog(rows)
                    st.success("✅ تم حفظ الصف وحالة الاعتماد")
                    st.rerun()
            elif delete_row:
                rows.pop(index)
                _persist_catalog(rows)
                st.success("تم حذف المنتج")
                st.rerun()
    approved_rows = [row for row in rows if row.get("approved")]
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["name", "type", "case_price", "pack_count", "unit_price", "notes", "image_path"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(approved_rows)
    st.download_button("⬇️ تنزيل الكتالوج المعتمد CSV", data=csv_buffer.getvalue().encode("utf-8-sig"), file_name="product_catalog.csv", mime="text/csv", key="catalog_csv_download")
    pdf_col1, pdf_col2 = st.columns(2)
    with pdf_col1:
        st.download_button("📄 تنزيل الكتالوج كامل PDF", data=utils.build_catalog_pdf(rows, "كتالوج المنتجات"), file_name="product_catalog.pdf", mime="application/pdf", key="catalog_pdf_download")
    with pdf_col2:
        st.download_button("📄 تنزيل المعتمد فقط PDF", data=utils.build_catalog_pdf(approved_rows, "كتالوج المنتجات المعتمدة"), file_name="approved_product_catalog.pdf", mime="application/pdf", key="approved_catalog_pdf_download")

def render_tab_images(blur_bg_opt, blur_intensity_val, logo_opacity, fit_auto_logo, logo_custom_w, logo_custom_h, brand_text_scale, brand_color, brand_position_choice, brand_offset_x, brand_offset_y, extra_brand_suffix, extra_text_scale, extra_color, extra_position_choice, extra_offset_x, extra_offset_y, chosen_size, enhance_quality_opt, sharpness_slider_val, quality_slider_val, logo_position_choice, logo_offset_x, logo_offset_y, color_preset, enable_crop_opt, crop_l, crop_t, crop_r, crop_b, total_target_video_duration, image_duration_per_slide, audio_mode, uploaded_custom_audio, font_choice, remove_logo_bg=True, smart_logo_position=False):
    st.subheader("🖼️ مصنع تجميل صور المنتجات وفيديوهات السلايد شو الذكية")
    uploaded_images = st.file_uploader("ارفع الصور:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="img_up_tab2")
    show_orig_toggle = st.checkbox("👁️ عرض الصور الأصلية", key="show_orig_tab2")
    st.info("✂️ القص اليدوي موجود في الشريط الجانبي: فعّل Crop وحدد القص من كل اتجاه قبل بدء المعالجة.")
    if not uploaded_images:
        render_catalog_panel()
        return

    st.markdown("### 📣 إعلان المنتج من الصورة")
    st.caption("اكتب تفاصيل أو اسطمبة اختيارية. سيقرأ النظام الصورة عبر Gemini المجاني أو OpenAI، وإلا سيستخدم القالب المحلي.")
    ai_status = utils.openai_status()
    with st.expander("🔐 حالة اتصال نموذج الرؤية", expanded=False):
        if ai_status["configured"]:
            provider_name = {"gemini": "Google Gemini", "anthropic": "Anthropic Claude", "openai": "OpenAI"}.get(ai_status.get("provider"), ai_status.get("provider", ""))
            st.success(f"المفتاح مقروء — المزود: {provider_name} — النموذج: {ai_status['model']}")
            st.caption(f"العنوان: {ai_status['base']}")
        else:
            st.warning("المفتاح غير مقروء. أضف GEMINI_API_KEY في Streamlit → Settings → Secrets، أو استخدم OPENAI_API_KEY.")
    ad_details = st.text_input("اسم المنتج أو تفاصيله:", key="ad_details")
    ad_template = st.text_area("اسطمبة الإعلان اليدوية (اختياري):", placeholder="مثال: {المنتج} — جودة عالية، اطلب الآن...", key="ad_template")
    with st.expander("✂️ استخراج البضاعة من الصورة (مثل Canva Background Remover / Magic Grab)", expanded=False):
        st.caption("حدد مستطيلًا يحيط بالمنتج فقط. سيتم عزل المنتج بخلفية شفافة، والصورة الأصلية لن تتغير.")
        try:
            preview = Image.open(io.BytesIO(uploaded_images[0].getvalue()))
            image_width, image_height = preview.size
            image_token = hashlib.sha1(uploaded_images[0].getvalue()).hexdigest()
            if st.session_state.get("extract_image_token") != image_token:
                st.session_state.extract_image_token = image_token
                st.session_state.extract_left = 0
                st.session_state.extract_top = 0
                st.session_state.extract_right = image_width
                st.session_state.extract_bottom = image_height
                st.session_state.pop("extracted_product_image", None)
            st.session_state.extract_left = max(0, min(int(st.session_state.get("extract_left", 0)), max(0, image_width - 1)))
            st.session_state.extract_top = max(0, min(int(st.session_state.get("extract_top", 0)), max(0, image_height - 1)))
            st.session_state.extract_right = max(st.session_state.extract_left + 1, min(int(st.session_state.get("extract_right", image_width)), image_width))
            st.session_state.extract_bottom = max(st.session_state.extract_top + 1, min(int(st.session_state.get("extract_bottom", image_height)), image_height))
            x1, x2 = st.columns(2)
            with x1:
                extract_left = st.slider("بداية المنتج من اليسار", 0, max(1, image_width - 1), key="extract_left")
                extract_top = st.slider("بداية المنتج من الأعلى", 0, max(1, image_height - 1), key="extract_top")
            with x2:
                extract_right = st.slider("نهاية المنتج من اليمين", 1, image_width, key="extract_right")
                extract_bottom = st.slider("نهاية المنتج من الأسفل", 1, image_height, key="extract_bottom")
            crop_preview = preview.convert("RGBA").copy()
            shade = Image.new("RGBA", crop_preview.size, (0, 0, 0, 0))
            shade_draw = ImageDraw.Draw(shade)
            shade_color = (0, 0, 0, 125)
            shade_draw.rectangle((0, 0, image_width, extract_top), fill=shade_color)
            shade_draw.rectangle((0, extract_bottom, image_width, image_height), fill=shade_color)
            shade_draw.rectangle((0, extract_top, extract_left, extract_bottom), fill=shade_color)
            shade_draw.rectangle((extract_right, extract_top, image_width, extract_bottom), fill=shade_color)
            crop_preview = Image.alpha_composite(crop_preview, shade)
            guide = ImageDraw.Draw(crop_preview)
            guide_width = max(8, min(image_width, image_height) // 110)
            guide.line([(extract_left, 0), (extract_left, image_height)], fill=(255, 55, 55, 255), width=guide_width)
            guide.line([(extract_right, 0), (extract_right, image_height)], fill=(255, 55, 55, 255), width=guide_width)
            guide.line([(0, extract_top), (image_width, extract_top)], fill=(255, 55, 55, 255), width=guide_width)
            guide.line([(0, extract_bottom), (image_width, extract_bottom)], fill=(255, 55, 55, 255), width=guide_width)
            guide.rectangle((extract_left, extract_top, extract_right, extract_bottom), outline=(255, 215, 0, 255), width=guide_width + 5)
            handle_radius = max(10, guide_width + 3)
            for handle_x, handle_y in ((extract_left, extract_top), (extract_right, extract_top), (extract_left, extract_bottom), (extract_right, extract_bottom)):
                guide.ellipse((handle_x - handle_radius, handle_y - handle_radius, handle_x + handle_radius, handle_y + handle_radius), fill=(255, 215, 0, 255), outline=(0, 0, 0, 255), width=3)
            label = f"X1 {extract_left}  Y1 {extract_top}   |   X2 {extract_right}  Y2 {extract_bottom}"
            label_width = max(80, min(540, image_width - 16))
            label_x = max(8, min(extract_left + 12, image_width - label_width - 8))
            label_y = max(8, min(extract_top + 12, image_height - 54))
            label_box = (label_x, label_y, label_x + label_width, label_y + 46)
            guide.rounded_rectangle(label_box, radius=10, fill=(0, 0, 0, 205), outline=(255, 215, 0, 255), width=2)
            guide.text((label_box[0] + 12, label_box[1] + 10), label, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
            st.image(crop_preview, caption=f"المعاينة الحية — العرض: {extract_right - extract_left}px | الارتفاع: {extract_bottom - extract_top}px", width="stretch")
            selected_preview = preview.crop((extract_left, extract_top, extract_right, extract_bottom))
            st.image(selected_preview, caption="لقطة مكبرة للجزء الذي سيتم استخراجه", width="stretch")
            st.caption(f"الخطوط الحمراء هي حدود الإحداثيات، والإطار الأصفر يحدد الجزء الذي سيتم عزله. القص النهائي يتم من الصورة الأصلية PNG بدون تصغير أو ضغط فاقد للجودة. الإحداثيات: ({extract_left},{extract_top}) → ({extract_right},{extract_bottom}).")
            if st.button("✨ استخراج المنتج بخلفية شفافة", key="extract_product_button"):
                if extract_right <= extract_left or extract_bottom <= extract_top:
                    st.error("خلي نهاية المستطيل بعد بدايته.")
                else:
                    extracted = extract_product_from_image(uploaded_images[0].getvalue(), extract_left, extract_top, extract_right, extract_bottom)
                    if extracted:
                        st.session_state.extracted_product_image = extracted
                        st.success("تم عزل المنتج — راجع النتيجة قبل إضافتها للكتالوج.")
                    else:
                        st.error("لم نقدر نعزل المنتج من المنطقة المحددة. وسّع المستطيل حول المنتج وجرب مرة ثانية.")
            if st.session_state.get("extracted_product_image"):
                st.image(st.session_state.extracted_product_image, caption="المنتج المعزول بخلفية شفافة", width="stretch")
                st.download_button("تنزيل صورة المنتج المعزولة", data=st.session_state.extracted_product_image, file_name="product-cutout.png", mime="image/png", key="download_extracted_product")
        except Exception:
            st.error("تعذر قراءة الصورة لتحديد منطقة المنتج.")
    with st.expander("📝 تحسين قراءة النص داخل الصورة", expanded=False):
        st.caption("أداة Copilot احتياطية لتحسين وضوح النص في نسخة منفصلة، ولا تغيّر الصورة الأصلية.")
        st.caption("مسح الكلام آليًا مناسب للنص الواضح فوق خلفية بسيطة، وقد يحتاج مراجعة يدوية في الصور المزدحمة.")
        clean_col, remove_col = st.columns(2)
        with clean_col:
            if st.button("تحسين قراءة النص", key="cleanup_image_text"):
                cleaned_bytes = cleanup_text_from_image(uploaded_images[0].getvalue())
                if cleaned_bytes:
                    st.session_state.cleaned_text_image = cleaned_bytes
                    st.success("تم إنشاء نسخة محسّنة للقراءة")
                else:
                    st.error("تعذر قراءة الصورة")
        with remove_col:
            if st.button("مسح الكلام فعليًا", key="remove_image_text"):
                removed_bytes = remove_text_from_image(uploaded_images[0].getvalue())
                if removed_bytes:
                    st.session_state.removed_text_image = removed_bytes
                    st.success("تم إنشاء نسخة بعد مسح النص")
                else:
                    st.error("تعذر إزالة النص من الصورة")
        if st.session_state.get("cleaned_text_image"):
            st.image(st.session_state.cleaned_text_image, caption="نسخة تحسين القراءة — النص موجود", width="stretch")
            st.download_button("تنزيل نسخة تحسين القراءة", data=st.session_state.cleaned_text_image, file_name="text-enhanced.png", mime="image/png", key="download_cleaned_text")
        if st.session_state.get("removed_text_image"):
            st.image(st.session_state.removed_text_image, caption="نسخة مسح الكلام", width="stretch")
            st.download_button("تنزيل نسخة مسح الكلام", data=st.session_state.removed_text_image, file_name="text-removed.png", mime="image/png", key="download_removed_text")
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
            st.warning("تم استخدام القالب المحلي. راجع حالة نموذج الرؤية أعلى القسم وتأكد من إضافة مفتاح المزود في Secrets.")
        st.text_area("البوست الإعلاني الجاهز للتعديل والنسخ:", key="generated_ad_text", height=220)
    if st.session_state.get("trending_hashtags"):
        st.caption("هاشتاجات اليوم: " + " ".join(st.session_state.trending_hashtags))
    album_choice = "📥 ألبوم صور مفرودة منفصلة" if len(uploaded_images) == 1 else st.radio("اختر نمط التصدير:", ("📥 ألبوم صور مفرودة منفصلة", "🎬 دمجهم فيديو متحرك (Slideshow)", "🖼️ تجميع في صورة واحدة (Collage)"), key="alb_choice_tab2")
    if show_orig_toggle:
        for idx, img_file in enumerate(uploaded_images): st.image(img_file, caption=f"أصل صورة {idx + 1}", width="stretch")
        return
    if not st.button("⚙️ ابدأ معالجة الصور", key="btn_proc_imgs"): return
    saved_paths = []
    for index, img_file in enumerate(uploaded_images):
        temp_path = os.path.join(config.TMP_DIR, f"temp_prod_{index}.png")
        with open(temp_path, "wb") as stream: stream.write(img_file.getvalue())
        saved_paths.append(utils.process_image_template(temp_path, blur_background=blur_bg_opt, blur_intensity=blur_intensity_val, opacity_val=logo_opacity, fit_auto_logo=fit_auto_logo, logo_custom_w=logo_custom_w, logo_custom_h=logo_custom_h, brand_text_scale=brand_text_scale, brand_color=brand_color, brand_pos=brand_position_choice, brand_off_x=brand_offset_x, brand_off_y=brand_offset_y, extra_text=extra_brand_suffix, extra_text_scale=extra_text_scale, extra_color=extra_color, extra_pos=extra_position_choice, extra_off_x=extra_offset_x, extra_off_y=extra_offset_y, target_size=chosen_size, enhance_quality=enhance_quality_opt, sharpness_val=sharpness_slider_val, quality_val=quality_slider_val, logo_pos_mode=logo_position_choice, logo_off_x=logo_offset_x, logo_off_y=logo_offset_y, color_preset=color_preset, enable_crop=enable_crop_opt, c_left=crop_l, c_top=crop_t, c_right=crop_r, c_bottom=crop_b, font_choice=font_choice, remove_logo_bg=remove_logo_bg, smart_logo_position=smart_logo_position))
        if os.path.exists(temp_path): os.remove(temp_path)
    render_catalog_panel(saved_paths)
    if album_choice == "📥 ألبوم صور مفرودة منفصلة":
        st.success("🎉 تمت المعالجة بنجاح!")
        for idx, path in enumerate(saved_paths): st.image(path, caption=f"منتج {idx + 1}", width="stretch")
    elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
        st.image(utils.create_image_collage(saved_paths, chosen_size or (1080, 1080)), caption="صورة الكولاج", width="stretch")
    else:
        duration = total_target_video_duration / len(saved_paths) if total_target_video_duration else image_duration_per_slide
        with st.spinner("🎬 جاري رندرة السلايد شو..."):
            clips = [ImageClip(path).set_duration(duration) for path in saved_paths]
            video = concat_videoclips(clips, method="compose")
            video.write_videofile("slideshow_out.mp4", codec="libx264", fps=24, preset="ultrafast")
            st.video("slideshow_out.mp4")


def render_tab_store():
    """Simple customer-facing catalog: browse, cart, and handoff to WhatsApp."""
    st.markdown("# 🛍️ اختارها واطلبها")
    st.caption("اختار المنتج، ضيفه للسلة، وابعت طلبك على واتساب بدون تسجيل أو دفع إلكتروني.")
    direct_message = "مرحبًا، عايز أستفسر عن المنتجات والأسعار المتاحة."
    st.link_button("💬 تواصل مباشر على واتساب", f"https://wa.me/{config.CUSTOMER_WHATSAPP_NUMBER}?text={quote(direct_message)}")
    all_rows = [row for row in config.load_catalog() if row.get("approved") and row.get("name")]
    if not all_rows:
        st.info("المتجر لسه مستني منتجات معتمدة من تبويب الصور والمنتجات.")
        return
    public_url = config.STORE_PUBLIC_URL
    if not public_url:
        headers = getattr(st.context, "headers", {})
        host = headers.get("X-Forwarded-Host") or headers.get("Host")
        proto = headers.get("X-Forwarded-Proto", "https")
        public_url = f"{proto}://{host}" if host else ""
    categories = ["الكل"] + list(dict.fromkeys(row.get("type", "أخرى") for row in all_rows))
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔎 دور على منتج", key="store_search", placeholder="مثال: توكة أو مكياج")
    with col2:
        category = st.selectbox("القسم", categories, key="store_category")
    visible = [row for row in all_rows if (category == "الكل" or row.get("type") == category) and (not search.strip() or search.casefold() in row.get("name", "").casefold())]
    if not visible:
        st.warning("مفيش منتجات مطابقة للبحث الحالي.")
        return
    if "store_cart" not in st.session_state:
        st.session_state.store_cart = {}
    st.markdown(f"### المنتجات المتاحة ({len(visible)})")
    for index, row in enumerate(visible):
        product_id = str(row.get("id") or row.get("image_path") or row.get("name") or index)
        product_url = f"{public_url}?product_id={quote(product_id)}" if public_url else "رابط المتجر العام"
        product_price = float(row.get("unit_price") or 0)
        hashtag_name = re.sub(r"[^\w\u0600-\u06FF]+", "_", str(row.get("name"))).strip("_")
        share_text = (
            f"🛍️ {row.get('name')}\n"
            f"💰 السعر: {product_price:g} جنيه\n"
            f"📦 القسم: {row.get('type', 'أخرى')}\n"
            f"📝 {row.get('notes') or 'منتج مميز'}\n"
            f"🔗 رابط المنتج: {product_url}\n"
            f"💬 واتساب: https://wa.me/{config.CUSTOMER_WHATSAPP_NUMBER}\n"
            f"📱 كتالوج واتساب: https://wa.me/c/201125316241\n\n"
            f"#منتجك #اختارها_واطلبها #{hashtag_name}"
        )
        with st.container(border=True):
            left, right = st.columns([1, 2])
            with left:
                image_path = row.get("image_path", "")
                if image_path and os.path.exists(image_path):
                    st.image(image_path, width="stretch")
                else:
                    st.caption("الصورة غير متاحة")
            with right:
                st.markdown(f"### {row.get('name')}")
                st.caption(f"القسم: {row.get('type', 'أخرى')}")
                st.write(row.get("notes") or "منتج مميز")
                st.markdown(f"**{product_price:g} جنيه للقطعة**")
                quick_message = f"مرحبًا، عايز أعرف تفاصيل منتج: {row.get('name')} — السعر المعلن: {product_price:g} جنيه"
                st.link_button("💬 اسأل عن المنتج على واتساب", f"https://wa.me/{config.CUSTOMER_WHATSAPP_NUMBER}?text={quote(quick_message)}")
                with st.expander("📣 مشاركة المنتج على السوشيال"):
                    st.text_area("النص الجاهز للنسخ:", value=share_text, height=190, key=f"share_text_{product_id}")
                    share_encoded = quote(share_text)
                    share_col1, share_col2, share_col3 = st.columns(3)
                    with share_col1:
                        st.link_button("واتساب", f"https://wa.me/?text={share_encoded}")
                    with share_col2:
                        st.link_button("تليجرام", f"https://t.me/share/url?url={quote(product_url)}&text={share_encoded}")
                    with share_col3:
                        st.link_button("فيسبوك", f"https://www.facebook.com/sharer/sharer.php?u={quote(product_url)}")
                    st.link_button("إكس / Twitter", f"https://twitter.com/intent/tweet?text={share_encoded}&url={quote(product_url)}")
                    st.download_button("تنزيل نص المشاركة", data=share_text, file_name=f"share-{product_id}.txt", mime="text/plain", key=f"share_download_{product_id}")
                    st.caption("إنستجرام لا يوفر رابط مشاركة ويب يملأ المنشور تلقائيًا؛ انسخ النص والصورة وانشرهما من التطبيق.")
                qty = st.number_input("الكمية", min_value=0, max_value=99, value=0, step=1, key=f"store_qty_{product_id}")
                if st.button("🛒 أضف للسلة", key=f"store_add_{product_id}"):
                    if qty < 1:
                        st.warning("اختار كمية الأول")
                    else:
                        current = st.session_state.store_cart.get(product_id, {"row": row, "qty": 0})
                        current["row"] = row
                        current["qty"] = min(99, int(current.get("qty", 0)) + int(qty))
                        st.session_state.store_cart[product_id] = current
                        st.success("اتضاف للسلة")
    st.divider()
    st.markdown("## 🛒 سلتك")
    cart = st.session_state.store_cart
    if not cart:
        st.info("السلة فاضية — اختار منتج واضغط أضف للسلة.")
        return
    cart_left, cart_right = st.columns([2, 1])
    with cart_left:
        st.caption("عدّل الكمية من هنا قبل إرسال الطلب.")
    with cart_right:
        if st.button("🧹 تفريغ السلة", key="store_clear_cart"):
            st.session_state.store_cart = {}
            st.rerun()
    total = 0.0
    lines = []
    for product_id, item in list(cart.items()):
        row = item["row"]
        unit = float(row.get("unit_price") or 0)
        item_col, qty_col, remove_col = st.columns([3, 1, 1])
        with item_col:
            st.write(f"**{row.get('name')}** — {unit:g} جنيه للقطعة")
        with qty_col:
            qty = st.number_input("الكمية", min_value=1, max_value=99, value=max(1, int(item.get("qty", 1))), step=1, key=f"cart_qty_{product_id}")
        with remove_col:
            remove_item = st.button("حذف", key=f"cart_remove_{product_id}")
        if remove_item:
            del st.session_state.store_cart[product_id]
            st.rerun()
        st.session_state.store_cart[product_id]["qty"] = int(qty)
        subtotal = unit * int(qty)
        total += subtotal
        lines.append(f"- {row.get('name')} × {int(qty)} = {subtotal:g} جنيه")
    st.markdown(f"### الإجمالي: {total:g} جنيه")
    name = st.text_input("اسمك", key="store_customer_name")
    phone = st.text_input("رقم الهاتف", key="store_customer_phone")
    address = st.text_area("العنوان بالتفصيل", key="store_customer_address")
    notes = st.text_input("ملاحظات الطلب (اختياري)", key="store_customer_notes")
    if st.button("📲 اطلب على واتساب", type="primary", key="store_send_whatsapp"):
        if not name.strip() or not phone.strip() or not address.strip():
            st.error("اكتب الاسم ورقم الهاتف والعنوان علشان نقدر نتواصل معاك.")
        else:
            message = "طلب جديد من اختارها واطلبها\n\n" + "\n".join(lines) + f"\n\nالإجمالي: {total:g} جنيه\n\nالاسم: {name}\nالهاتف: {phone}\nالعنوان: {address}"
            if notes.strip():
                message += f"\nملاحظات: {notes}"
            st.link_button("فتح واتساب وإرسال الطلب", f"https://wa.me/{config.CUSTOMER_WHATSAPP_NUMBER}?text={quote(message)}")
            st.success("الطلب جاهز — اضغط زر فتح واتساب لإرساله.")


def render_tab_radar(current_channels):
    st.subheader("🛰️ رادار المنتجات اليدوي وكتالوج التصدير")
    st.caption("لا توجد متابعة في الخلفية: اضغط تشغيل الرادار لسحب دفعة واحدة من القنوات العامة، ثم راجع المنتجات قبل الاعتماد.")
    st.caption(f"إصدار الرادار: {config.APP_VERSION} — إذا ظهرت نتائج قديمة استخدم مسح الدفعة ثم شغّل الرادار من جديد.")

    col1, col2, col3 = st.columns(3)
    with col1:
        profit_percent = st.number_input("نسبة الربح (%)", min_value=0.0, max_value=300.0, value=35.0, step=1.0, key="radar_profit")
    with col2:
        max_messages = st.number_input("أقصى عدد رسائل", min_value=1, max_value=500, value=50, step=10, key="radar_max_messages")
    with col3:
        max_prices_text = st.text_input("حدود السعر الأصلي", value="0", key="radar_max_prices_text", help="اكتب أكثر من حد مفصولًا بفاصلة أو سطر، مثل: 120, 250, 500. المنتج يُقبل إذا كان سعره أقل من أو يساوي أي حد.")
    max_prices = []
    for raw_limit in re.split(r"[,،\n]+", max_prices_text):
        raw_limit = raw_limit.strip()
        if not raw_limit:
            continue
        try:
            parsed_limit = float(raw_limit)
            if parsed_limit > 0:
                max_prices.append(parsed_limit)
        except ValueError:
            pass
    if max_prices_text.strip() not in {"", "0"} and not max_prices:
        st.warning("اكتب حدود السعر كأرقام مفصولة بفاصلة، مثل: 120, 250, 500")

    channels_text = st.text_area("القنوات العامة المراد فحصها", value="\n".join(current_channels), height=90, key="radar_channels_text", help="اكتب username كل قناة في سطر، مع أو بدون @")
    source_rule = st.radio("ابدأ السحب من:", ("آخر الرسائل المتاحة", "من تاريخ", "بعد رسالة تحتوي على نص"), horizontal=True, key="radar_source_rule")
    date_from = st.date_input("التاريخ من", value=__import__('datetime').date.today(), key="radar_date_from") if source_rule == "من تاريخ" else None
    marker_text = st.text_input("نص علامة البداية", placeholder="مثال: ابدأ من هنا", key="radar_marker_text") if source_rule == "بعد رسالة تحتوي على نص" else ""
    allowed_forwarders_text = st.text_area("أسماء المصادر/المعلنين المسموح بهم (اختياري)", height=70, key="radar_allowed_forwarders", help="اكتب اسم المعلن كما يظهر في تيليجرام، كل اسم في سطر. اتركه فارغًا لاستبعاد أي منشور Forward.")
    exclude_forwarded = st.checkbox("استبعاد أي منشور منقول من معلن غير موجود بالقائمة", key="radar_exclude_forwarded")
    rounding = st.checkbox("تقريب السعر لأقرب 5 (2.5 أو أقل للأسفل، أكبر من 2.5 للأعلى)", key="radar_rounding")

    st.markdown("### بعد مراجعة المنتجات")
    review_required = st.checkbox("مراجعة يدوية لكل منتج قبل الاعتماد", key="radar_review_required")
    auto_publish_enabled = st.checkbox("السماح بالنشر التلقائي بعد الضغط على زر النشر", key="radar_auto_publish")
    publish_channel = st.text_input("قناة النشر الاختيارية", placeholder="@my_channel", key="radar_publish_channel")

    if "radar_products" not in st.session_state:
        st.session_state.radar_products = []

    clear_col, status_col = st.columns([1, 2])
    with clear_col:
        if st.button("🧹 مسح الدفعة القديمة", key="radar_clear_batch"):
            st.session_state.radar_products = []
            for key in list(st.session_state.keys()):
                if str(key).startswith("radar_approved_"):
                    del st.session_state[key]
            st.rerun()
    with status_col:
        if st.session_state.radar_products:
            st.info(f"هناك {len(st.session_state.radar_products)} منتجًا محفوظًا في جلسة الرادار.")

    if st.button("🛰️ تشغيل الرادار الآن", type="primary", key="radar_scan_now"):
        channels = [line.strip().lstrip('@') for line in channels_text.splitlines() if line.strip()]
        if not channels:
            st.error("أدخل قناة عامة واحدة على الأقل.")
        else:
            found = []
            with st.spinner("جاري فحص القنوات العامة مرة واحدة..."):
                try:
                    for channel in channels:
                        allowed_forwarders = [line.strip() for line in allowed_forwarders_text.splitlines() if line.strip()]
                        batch = utils.fetch_public_channel_messages(channel, date_from=date_from, marker_text=marker_text, max_messages=int(max_messages), allowed_forwarders=allowed_forwarders, exclude_forwarded=exclude_forwarded)
                        for item in batch:
                            if max_prices and not any(float(item.get('auto_price') or 0) <= limit for limit in max_prices):
                                continue
                            found.append(utils.build_catalog_product(item, profit_percent, rounding))
                    # Remove duplicates while preserving source order.
                    unique = {}
                    for product in found:
                        unique[product['id']] = product
                    st.session_state.radar_products = list(unique.values())
                    for product in st.session_state.radar_products:
                        product.setdefault("id", uuid.uuid4().hex)
                        st.session_state[f"radar_approved_{product['id']}"] = False
                    st.success(f"تم العثور على {len(st.session_state.radar_products)} منتجًا. راجعها قبل التصدير أو النشر.")
                except Exception as exc:
                    st.error(f"تعذر فحص القنوات: {exc}")

    products = st.session_state.get("radar_products", [])
    if not products:
        st.info("لم يتم تحميل منتجات بعد. اكتب القنوات وحدد البداية ثم اضغط تشغيل الرادار.")
        return

    # Migrate products created before price cleanup so the old price cannot remain
    # in a title/description after a deployment or Streamlit rerun.
    for product in products:
        product["title"] = utils.remove_original_prices(product.get("title", "")).strip() or "منتج جديد"
        product["description"] = utils.remove_original_prices(product.get("description", "")).strip()

    st.markdown(f"### المنتجات المكتشفة ({len(products)})")
    if st.button("✅ تحديد كل المنتجات للمراجعة", key="radar_approve_all"):
        for product in products:
            product.setdefault("id", uuid.uuid4().hex)
            product['approved'] = True
            st.session_state[f"radar_approved_{product['id']}"] = True
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
                st.caption(f"تم حساب سعر البيع حسب نسبة الربح المحددة: {product.get('profit_percent', 0):g}%")
            with source_col:
                st.caption(f"المصدر: @{product.get('source_channel', '')}")
                st.caption(f"التاريخ: {product.get('source_date', '') or 'غير متاح'}")
            if review_required:
                product.setdefault("id", uuid.uuid4().hex)
                approval_key = f"radar_approved_{product['id']}"
                if approval_key not in st.session_state:
                    st.session_state[approval_key] = bool(product.get('approved', False))
                product['approved'] = st.checkbox("أوافق على اعتماد هذا المنتج", key=approval_key)
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
