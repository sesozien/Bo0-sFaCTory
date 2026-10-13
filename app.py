import os
import json
import streamlit as st
from PIL import Image

import config
import utils
import tabs

st.set_page_config(page_title=config.PAGE_TITLE, page_icon=config.PAGE_ICON, layout="centered")
current_channels = config.load_and_sync_channels()

if not os.path.exists(config.DEFAULT_LOGO_PATH):
    Image.new('RGBA', (200, 200), color=(255, 75, 75, 255)).save(config.DEFAULT_LOGO_PATH)
if not os.path.exists(config.ACTIVE_LOGO_PATH):
    Image.open(config.DEFAULT_LOGO_PATH).save(config.ACTIVE_LOGO_PATH)

DEFAULT_SETTINGS = {
    "l_pos": "فوق يمين (Top-Right)",
    "l_ox": 0, "l_oy": 0,
    "logo_opacity": 0.8,
    "logo_fit_auto": False,
    "logo_custom_w": 200, "logo_custom_h": 200,
    "b_pos": "تحت شمال (Bottom-Left)",
    "b_ox": 0, "b_oy": 0,
    "b_sc": 0.035, "b_cl": "#FFD700",
    "e_pos": "تحت يمين (Bottom-Right)",
    "e_ox": 0, "e_oy": 0,
    "e_sc": 0.025, "e_cl": "#FFFFFF",
    "blur_bg": True,
    "blur_val": 15,
    "enhance_opt": True,
    "sharp_val": 2.0,
    "quality_val": 95,
    "color_preset": "طبيعي (بدون فلتر)",
    "dynamic_brand_text": "Montgk Brand"
}

for k, v in DEFAULT_SETTINGS.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .web-banner {
        background: linear-gradient(135deg, #111115 0%, #ff4b4b 100%);
        padding: 35px; border-radius: 15px; text-align: center;
        box-shadow: 0px 6px 20px rgba(255, 75, 75, 0.4); margin-bottom: 25px;
    }
    .banner-title { color: #ffffff; font-size: 38px; font-weight: bold; }
    .banner-subtitle { color: #e0e0e0; font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="web-banner">
        <div class="banner-title">🥷 Mr:- Bo0</div>
        <div class="banner-subtitle">{config.BRAND_NAME_AR} (Ultra Smart Edition)</div>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h2>🛰️ إعدادات المصنع الذكي</h2>", unsafe_allow_html=True)
    
    st.markdown("### 💰 تخصيص كلمات الأسعار الذكية")
    current_kw = config.get_price_keywords()
    st.caption("الكلمات المفتاحية: " + ", ".join(current_kw))
    new_kw = st.text_input("أضف كلمة جديدة (مثل: بـ):")
    if st.button("➕ حفظ الكلمة"):
        if new_kw and new_kw not in current_kw:
            current_kw.append(new_kw.strip())
            with open(config.KEYWORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(current_kw, f, ensure_ascii=False, indent=4)
            st.success("✅ تمت الإضافة وتحديث النظام الذكي!")
            st.rerun()

    st.write("---")
    color_preset = st.selectbox("فلتر الألوان الذكي:", ["طبيعي (بدون فلتر)", "زاهي ومشرق (Vibrant Product)", "تباين دافئ (Warm Pop)", "سينمائي داكن (Cinematic Dark)", "أبيض وأسود فاخر (Black & White)"], key="c_preset")
    
    platform_dim = st.selectbox("مَقاس منصة العرض:", ["تلقائي (حجم الملف الأصلي)", "تيك توك / ريلز (9:16 - 1080x1920)", "يوتيوب عريض (16:9 - 1920x1080)", "فيسبوك وانستجرام مربع (1:1 - 1080x1080)"])
    dim_map = {"تلقائي (حجم الملف الأصلي)": None, "تيك توك / ريلز (9:16 - 1080x1920)": (1080, 1920), "يوتيوب عريض (16:9 - 1920x1080)": (1920, 1080), "فيسبوك وانستجرام مربع (1:1 - 1080x1080)": (1080, 1080)}
    chosen_size = dim_map[platform_dim]

    st.write("---")
    st.markdown("### 🔤 اختيار نوع الخط للكتابة (عربي وإنجليزي)")
    font_choice = st.selectbox("اختر نوع الخط المفضل:", [
        "Cairo (عربي عريض فاخر)", 
        "Tajawal (عربي أنيق وانسيابي)", 
        "Amiri (عربي كلاسيكي أصيل)", 
        "Roboto (إنجليزي مودرن وسريع)", 
        "Montserrat (إنجليزي عريض وبارز)"
    ], key="font_sel")

    st.write("---")
    st.markdown("### 🎯 التحكم الدقيق في اللوجو والشفافية")
    logo_pos = st.selectbox("مكان اللوجو الأساسي:", ["إحداثيات حرة ومباشرة (Custom X/Y)", "فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)", "تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)"], key="l_pos")
    logo_ox = st.slider("الإحداثي الأفقي (X):", -1000, 1000, 0, key="l_ox")
    logo_oy = st.slider("الإحداثي الرأسي (Y):", -1000, 1000, 0, key="l_oy")
    logo_opacity = st.slider("شفافية اللوجو (Opacity %):", 0.1, 1.0, 0.8, key="l_op")
    fit_auto_logo = st.checkbox("تكيف اللوجو التلقائي (Auto Fit)", key="logo_fit_auto")
    
    c_lw, c_lh = st.columns(2)
    with c_lw: logo_w = st.slider("عرض اللوجو (px):", 10, 1000, 200, key="logo_w")
    with c_lh: logo_h = st.slider("ارتفاع اللوجو (px):", 10, 1000, 200, key="logo_h")

    st.write("---")
    st.markdown("### 🏷️ اسم البراند")
    input_brand_text = st.text_input("نص البراند:", value="Montgk Brand", key="dynamic_brand_text")
    os.environ["dynamic_brand_text"] = input_brand_text
    brand_pos = st.selectbox("مكان البراند:", ["تحت شمال (Bottom-Left)", "تحت يمين (Bottom-Right)", "فوق شمال (Top-Left)", "فوق يمين (Top-Right)", "في المنتصف تماماً (Center)"], key="b_pos")
    brand_ox = st.slider("مسافة أفقي للبراند:", -300, 300, 0, key="b_ox")
    brand_oy = st.slider("مسافة رأسي للبراند:", -300, 300, 0, key="b_oy")
    brand_sc = st.slider("حجم خط البراند:", 0.015, 0.080, 0.035, key="b_sc")
    brand_cl = st.color_picker("لون خط البراند:", "#FFD700", key="b_cl")

    st.write("---")
    st.markdown("### ✍️ الجملة الإضافية")
    extra_suffix = st.text_input("الجملة الإضافية:", value="", key="e_text")
    extra_pos = st.selectbox("مكان الجملة الإضافية:", ["تحت يمين (Bottom-Right)", "تحت شمال (Bottom-Left)", "فوق يمين (Top-Right)", "فوق شمال (Top-Left)", "في المنتصف تماماً (Center)"], key="e_pos")
    extra_ox = st.slider("مسافة أفقي للجملة:", -300, 300, 0, key="e_ox")
    extra_oy = st.slider("مسافة رأسي للجملة:", -300, 300, 0, key="e_oy")
    extra_sc = st.slider("حجم خط الجملة:", 0.010, 0.060, 0.025, key="e_sc")
    extra_cl = st.color_picker("لون خط الجملة:", "#FFFFFF", key="e_cl")

    st.write("---")
    st.markdown("### 🖼️ خيارات الخلفية الذكية والجودة")
    blur_bg_opt = st.checkbox("تفعيل خلفية Blur (لو لم تُفعل تصبح بيضاء سادة)", value=True, key="blur_bg")
    blur_intensity_val = st.slider("قوة التغبيش (Blur):", 1, 30, 15, key="blur_val")
    enhance_quality_opt = st.checkbox("تفعيل فلتر الجودة والحدة", value=True, key="enhance_opt")
    sharpness_slider_val = st.slider("حدة التفاصيل:", 0.0, 5.0, 2.0, key="sharp_val")
    quality_slider_val = st.slider("جودة الضغط (%):", 10, 100, 95, key="q_val")
    
    enable_crop_opt = st.checkbox("تفعيل قص أطراف الصور (Crop)", key="enable_crop")
    if enable_crop_opt:
        crop_l = st.slider("قص يسار:", 0, 500, 0, key="c_l")
        crop_t = st.slider("قص أعلى:", 0, 500, 0, key="c_t")
        crop_r = st.slider("قص يمين:", 0, 500, 0, key="c_r")
        crop_b = st.slider("قص أسفل:", 0, 500, 0, key="c_b")
    else:
        crop_l = crop_t = crop_r = crop_b = 0

    if utils.ensure_valid_image(config.ACTIVE_LOGO_PATH):
        st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط (يتم تفريغ خلفيته أوتوماتيك)", width=100)
    uploaded_logo = st.file_uploader("تغيير اللوجو:", type=["png", "jpg", "jpeg"])
    if uploaded_logo is not None:
        Image.open(uploaded_logo).save(config.ACTIVE_LOGO_PATH)
        st.success("✅ تم تحديث اللوجو وتفريغه بنجاح!")
        st.rerun()

    audio_mode = st.radio("مصدر الصوت:", ["تراك المزيكا الحصري التلقائي", "رفع تراك أوديو MP3 مخصص من جهازك"])
    uploaded_custom_audio = st.file_uploader("ارفع الأوديو:", type=["mp3", "wav", "ogg"]) if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" else None

tab1, tab2, tab3, tab4 = st.tabs([
    "🎬 تشفير وتقطيع ومونتاج الفيديو", 
    "🖼️ قالب ألبومات وصور المنتجات", 
    "🛰️ رادار القنوات والـ Forward",
    "🔥 رادار الترندات واسطمبة البوستات"
])

with tab1:
    tabs.render_tab_video(chosen_size, logo_pos, logo_ox, logo_oy, logo_opacity, logo_w, logo_h, audio_mode, uploaded_custom_audio)

with tab2:
    tabs.render_tab_images(blur_bg_opt, blur_intensity_val, logo_opacity, fit_auto_logo, logo_w, logo_h, brand_sc, brand_cl, brand_pos, brand_ox, brand_oy, extra_suffix, extra_sc, extra_cl, extra_pos, extra_ox, extra_oy, chosen_size, enhance_quality_opt, sharpness_slider_val, quality_slider_val, logo_pos, logo_ox, logo_oy, color_preset, enable_crop_opt, crop_l, crop_t, crop_r, crop_b, None, 3, audio_mode, uploaded_custom_audio, font_choice)

with tab3:
    tabs.render_tab_radar(current_channels)

with tab4:
    tabs.render_tab_trends()
