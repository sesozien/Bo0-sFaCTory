"""Bo0'sViDClone Streamlit entry point.

This file owns application bootstrapping, shared widget state, and layout only.
Feature implementations live in tabs.py; reusable logic lives in utils.py.
"""
import json
import os

import streamlit as st
from PIL import Image

import config
import tabs
import utils


st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="centered")

DEFAULT_WIDGETS = {
    "c_preset": "طبيعي (بدون فلتر)",
    "platform_dim": "تلقائي (حجم الملف الأصلي)",
    "font_sel": "Cairo (عربي عريض فاخر)",
    "l_pos": "فوق يمين (Top-Right)", "l_ox": 0, "l_oy": 0, "l_op": 0.8,
    "logo_fit_auto": False, "rem_bg_chk": True, "logo_mode": "🤖 تلقائي ذكي", "logo_w": 200, "logo_h": 200,
    "dynamic_brand_text": "Montgk Brand",
    "b_pos": "تحت شمال (Bottom-Left)", "b_ox": 0, "b_oy": 0, "b_sc": 0.035, "b_cl": "#FFD700",
    "e_text": "", "e_pos": "تحت يمين (Bottom-Right)", "e_ox": 0, "e_oy": 0, "e_sc": 0.025, "e_cl": "#FFFFFF",
    "blur_bg": True, "blur_val": 15, "enhance_opt": True, "sharp_val": 2.0, "q_val": 95,
    "enable_crop": False, "c_l": 0, "c_t": 0, "c_r": 0, "c_b": 0,
    "audio_mode": "تراك المزيكا الحصري التلقائي",
    "vid_option_main": "لصق رابط فيديو (يوتيوب، فيسبوك، تيك توك)",
    "enable_trim_key": False, "t_start": 0, "t_end": 0,
    "sp_mode": "تسريع / تبطيء يدوي", "sp_factor": 1.0, "t_dur_sec": 15,
    "show_orig_tab2": False, "p_rate": config.DEFAULT_PRICE_INC_RATE,
    "b_items": config.DEFAULT_BOX_ITEMS_COUNT, "fb_url": "https://www.facebook.com/montgk1",
    "max_p": 5000, "d_filt": "كل البوستات المتاحة للقناة",
    "r_mode": "🛰️ سحب رادار حي وفوري", "trend_cat": "الكل",
}


def initialize_files():
    os.makedirs(config.TMP_DIR, exist_ok=True)
    if not utils.ensure_valid_image(config.DEFAULT_LOGO_PATH):
        Image.new("RGBA", (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)
    if not utils.ensure_valid_image(config.ACTIVE_LOGO_PATH):
        Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)
    config.get_price_keywords()


def initialize_state():
    saved = config.load_settings()
    for key, default in DEFAULT_WIDGETS.items():
        if key not in st.session_state:
            st.session_state[key] = saved.get(key, default)
    if "cached_posts" not in st.session_state:
        st.session_state.cached_posts = []
    if "product_price_index" not in st.session_state:
        st.session_state.product_price_index = {}


def render_sidebar():
    with st.sidebar:
        st.markdown("<h2>🛰️ إعدادات المصنع الذكي</h2>", unsafe_allow_html=True)
        st.markdown("### 💰 كلمات الأسعار الذكية")
        keywords = config.get_price_keywords()
        st.caption("الكلمات المفتاحية: " + ", ".join(keywords))
        new_keyword = st.text_input("أضف كلمة جديدة (مثل: بـ):", key="new_keyword")
        if st.button("➕ حفظ الكلمة", key="save_keyword"):
            if new_keyword and new_keyword.strip() not in keywords:
                keywords.append(new_keyword.strip())
                with open(config.KEYWORDS_FILE, "w", encoding="utf-8") as stream:
                    json.dump(keywords, stream, ensure_ascii=False, indent=4)
                st.success("✅ تمت الإضافة وتحديث النظام الذكي!")
                st.rerun()

        st.write("---")
        color_preset = st.selectbox("فلتر الألوان الذكي:", [
            "طبيعي (بدون فلتر)", "زاهي ومشرق (Vibrant Product)", "تباين دافئ (Warm Pop)",
            "سينمائي داكن (Cinematic Dark)", "أبيض وأسود فاخر (Black & White)"], key="c_preset")
        dim_map = {
            "تلقائي (حجم الملف الأصلي)": None,
            "تيك توك / ريلز (9:16 - 1080x1920)": (1080, 1920),
            "يوتيوب عريض (16:9 - 1920x1080)": (1920, 1080),
            "فيسبوك وانستجرام مربع (1:1 - 1080x1080)": (1080, 1080),
        }
        platform_dim = st.selectbox("مَقاس منصة العرض:", list(dim_map), key="platform_dim")
        chosen_size = dim_map[platform_dim]

        st.write("---")
        font_choice = st.selectbox("اختر الخط المفضل:", [
            "Cairo (عربي عريض فاخر)", "Tajawal (عربي أنيق وانسيابي)",
            "Amiri (عربي كلاسيكي أصيل)", "Roboto (إنجليزي مودرن وسريع)",
            "Montserrat (إنجليزي عريض وبارز)"], key="font_sel")

        st.write("---")
        st.markdown("### 🎯 اللوجو والكتابة")
        logo_positions = ["إحداثيات حرة ومباشرة (Custom X/Y)", "فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)", "تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)"]
        logo_mode = st.radio("طريقة وضع اللوجو:", ("🤖 تلقائي ذكي", "✋ يدوي"), horizontal=True, key="logo_mode")
        st.caption("التلقائي يختار الركن الأقل ازدحامًا، واليدوي يستخدم المكان والإحداثيات التي تحددها.")
        logo_pos = st.selectbox("مكان اللوجو الأساسي:", logo_positions, key="l_pos")
        logo_ox = st.slider("الإحداثي الأفقي (X):", -1000, 1000, key="l_ox")
        logo_oy = st.slider("الإحداثي الرأسي (Y):", -1000, 1000, key="l_oy")
        logo_opacity = st.slider("شفافية اللوجو:", 0.1, 1.0, key="l_op")
        fit_auto_logo = st.checkbox("تكيف اللوجو التلقائي (Auto Fit)", key="logo_fit_auto")
        remove_logo_bg = st.checkbox("🫥 إزالة الخلفية البيضاء للوجو تلقائياً", key="rem_bg_chk")
        logo_w = st.slider("عرض اللوجو (px):", 10, 1000, key="logo_w")
        logo_h = st.slider("ارتفاع اللوجو (px):", 10, 1000, key="logo_h")
        if utils.ensure_valid_image(config.ACTIVE_LOGO_PATH):
            st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط الحالي", width=100)
        uploaded_logo = st.file_uploader("تغيير اللوجو:", type=["png", "jpg", "jpeg"], key="logo_uploader_safe")
        if uploaded_logo is not None and uploaded_logo.getvalue():
            with open(config.ACTIVE_LOGO_PATH, "wb") as stream:
                stream.write(uploaded_logo.getvalue())
            st.success("✅ تم تحديث اللوجو بنجاح!")
            st.rerun()

        st.write("---")
        input_brand_text = st.text_input("نص البراند:", key="dynamic_brand_text")
        os.environ["dynamic_brand_text"] = input_brand_text
        brand_pos = st.selectbox("مكان البراند:", ["تحت شمال (Bottom-Left)", "تحت يمين (Bottom-Right)", "فوق شمال (Top-Left)", "فوق يمين (Top-Right)", "في المنتصف تماماً (Center)"], key="b_pos")
        brand_ox = st.slider("مسافة أفقي للبراند:", -300, 300, key="b_ox")
        brand_oy = st.slider("مسافة رأسي للبراند:", -300, 300, key="b_oy")
        brand_sc = st.slider("حجم خط البراند:", 0.015, 0.080, key="b_sc")
        brand_cl = st.color_picker("لون خط البراند:", key="b_cl")
        extra_suffix = st.text_input("الجملة الإضافية:", key="e_text")
        extra_pos = st.selectbox("مكان الجملة الإضافية:", ["تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)", "فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)"], key="e_pos")
        extra_ox = st.slider("مسافة أفقي للجملة:", -300, 300, key="e_ox")
        extra_oy = st.slider("مسافة رأسي للجملة:", -300, 300, key="e_oy")
        extra_sc = st.slider("حجم خط الجملة:", 0.010, 0.060, key="e_sc")
        extra_cl = st.color_picker("لون خط الجملة:", key="e_cl")

        st.write("---")
        blur_bg = st.checkbox("تفعيل خلفية Blur", key="blur_bg")
        blur_val = st.slider("قوة التغبيش (Blur):", 1, 30, key="blur_val")
        enhance = st.checkbox("تفعيل فلتر الجودة والحدة", key="enhance_opt")
        sharp = st.slider("حدة التفاصيل:", 0.0, 5.0, key="sharp_val")
        quality = st.slider("جودة الضغط (%):", 10, 100, key="q_val")
        enable_crop = st.checkbox("✂️ تفعيل قص أطراف الصور (Crop)", key="enable_crop")
        crop = [st.slider(label, 0, 500, key=key) for label, key in [("قص يسار:", "c_l"), ("قص أعلى:", "c_t"), ("قص يمين:", "c_r"), ("قص أسفل:", "c_b")]] if enable_crop else [0, 0, 0, 0]
        audio_mode = st.radio("مصدر الصوت:", ["تراك المزيكا الحصري التلقائي", "رفع تراك أوديو MP3 مخصص من جهازك"], key="audio_mode")
        custom_audio = st.file_uploader("ارفع الأوديو:", type=["mp3", "wav", "ogg"], key="custom_audio") if audio_mode.startswith("رفع") else None

    return {
        "chosen_size": chosen_size, "font_choice": font_choice, "logo_pos": logo_pos,
        "logo_ox": logo_ox, "logo_oy": logo_oy, "logo_opacity": logo_opacity,
        "fit_auto_logo": fit_auto_logo, "smart_logo": logo_mode == "🤖 تلقائي ذكي", "remove_logo_bg": remove_logo_bg, "logo_w": logo_w, "logo_h": logo_h,
        "brand_pos": brand_pos, "brand_ox": brand_ox, "brand_oy": brand_oy, "brand_sc": brand_sc, "brand_cl": brand_cl,
        "extra_suffix": extra_suffix, "extra_pos": extra_pos, "extra_ox": extra_ox, "extra_oy": extra_oy, "extra_sc": extra_sc, "extra_cl": extra_cl,
        "blur_bg": blur_bg, "blur_val": blur_val, "enhance": enhance, "sharp": sharp, "quality": quality,
        "crop": crop, "audio_mode": audio_mode, "custom_audio": custom_audio,
    }


def main():
    initialize_files()
    initialize_state()
    channels = config.load_and_sync_channels()
    settings = render_sidebar()
    st.markdown("<style>.main{background-color:#0e1117}.web-banner{background:linear-gradient(135deg,#111115 0%,#ff4b4b 100%);padding:35px;border-radius:15px;text-align:center;margin-bottom:25px}.banner-title{color:#fff;font-size:38px;font-weight:bold}.banner-subtitle{color:#e0e0e0;font-size:20px}</style>", unsafe_allow_html=True)
    st.markdown(f'<div class="web-banner"><div class="banner-title">Mr:- Bo0</div><div class="banner-subtitle">{config.BRAND_NAME_AR} (Clean App Edition)</div></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🎬 الفيديو", "🖼️ الصور والمنتجات", "🛰️ رادار القنوات", "🔥 الترندات"])
    with tab1:
        tabs.render_tab_video(settings["chosen_size"], settings["logo_pos"], settings["logo_ox"], settings["logo_oy"], settings["logo_opacity"], settings["logo_w"], settings["logo_h"], settings["audio_mode"], settings["custom_audio"])
    with tab2:
        tabs.render_tab_images(settings["blur_bg"], settings["blur_val"], settings["logo_opacity"], settings["fit_auto_logo"], settings["logo_w"], settings["logo_h"], settings["brand_sc"], settings["brand_cl"], settings["brand_pos"], settings["brand_ox"], settings["brand_oy"], settings["extra_suffix"], settings["extra_sc"], settings["extra_cl"], settings["extra_pos"], settings["extra_ox"], settings["extra_oy"], settings["chosen_size"], settings["enhance"], settings["sharp"], settings["quality"], settings["logo_pos"], settings["logo_ox"], settings["logo_oy"], st.session_state.c_preset, settings["crop"] != [0, 0, 0, 0], *settings["crop"], 60, 5, settings["audio_mode"], settings["custom_audio"], settings["font_choice"], settings["remove_logo_bg"], settings["smart_logo"])
    with tab3:
        tabs.render_tab_radar(channels)
    with tab4:
        tabs.render_tab_trends()

    config.save_settings(st.session_state)


if __name__ == "__main__":
    main()
