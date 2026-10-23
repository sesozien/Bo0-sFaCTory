import os
import re
import json
import requests
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance, ImageOps
import arabic_reshaper
from bidi.algorithm import get_display
import streamlit as st
from bs4 import BeautifulSoup

# مكتبات الفيديو والصوت
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips as concat_videoclips
import moviepy.video.fx as vfx
import yt_dlp

# استيراد الإعدادات البسيطة من config
import config

# =========================================================
# دوال المعالجة (مدمجة مباشرة هنا لضمان عدم وجود أي إيرور)
# =========================================================
def ensure_valid_image(image_path):
    if not os.path.exists(image_path):
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False

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

def get_selected_font(font_choice, font_size=24):
    font_urls = {
        "Cairo (عربي عريض فاخر)": "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf",
        "Tajawal (عربي أنيق وانسيابي)": "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Bold.ttf",
        "Amiri (عربي كلاسيكي أصيل)": "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf",
        "Roboto (إنجليزي مودرن وسريع)": "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Bold.ttf",
        "Montserrat (إنجليزي عريض وبارز)": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf"
    }
    target_url = font_urls.get(font_choice, font_urls["Cairo (عربي عريض فاخر)"])
    font_dir = os.path.join(os.path.expanduser("~"), ".fonts")
    os.makedirs(font_dir, exist_ok=True)
    font_filename = font_choice.split()[0] + "-Bold.ttf"
    font_path = os.path.join(font_dir, font_filename)
    
    if not os.path.exists(font_path):
        try:
            r = requests.get(target_url, timeout=15)
            with open(font_path, "wb") as f: f.write(r.content)
        except:
            pass
    try:
        return ImageFont.truetype(font_path, font_size)
    except:
        return ImageFont.load_default()

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def calculate_exact_position(img_w, img_h, elem_w, elem_h, pos_mode, off_x, off_y):
    if pos_mode == "إحداثيات حرة ومباشرة (Custom X/Y)":
        x = off_x
        y = off_y
    else:
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
    if x + elem_w > img_w: x = max(0, img_w - elem_w)
    if y + elem_h > img_h: y = max(0, img_h - elem_h)
    
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
    
    bx, by = calculate_exact_position(w, h, box_w, box_h, pos_mode, off_x, off_y)
    
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=10, fill=(0, 0, 0, 140))
    img.alpha_composite(overlay)
    
    draw = ImageDraw.Draw(img)
    text_position = (bx + pad_x, by + pad_y - 2)
    
    draw.text((text_position[0] + 2, text_position[1] + 2), bidi_text, fill=(0, 0, 0, 220), font=font)
    draw.text(text_position, bidi_text, fill=fill_color, font=font)

def process_image_template(image_path, blur_background=True, blur_intensity=12, opacity_val=0.8, 
                           fit_auto_logo=False, logo_custom_w=200, logo_custom_h=200,
                           brand_text_scale=0.035, brand_color="#FFD700", brand_pos="تحت شمال (Bottom-Left)", brand_off_x=0, brand_off_y=0,
                           extra_text="", extra_text_scale=0.025, extra_color="#FFFFFF", extra_pos="تحت يمين (Bottom-Right)", extra_off_x=0, extra_off_y=0,
                           target_size=None, enhance_quality=True, sharpness_val=2.0, quality_val=95, logo_pos_mode="فوق يمين (Top-Right)", logo_off_x=0, logo_off_y=0,
                           color_preset="طبيعي (بدون فلتر)", enable_crop=False, c_left=0, c_top=0, c_right=0, c_bottom=0, font_choice="Cairo (عربي عريض فاخر)", remove_logo_bg=True):
    
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
        if sharpness_val > 0:
            img = ImageEnhance.Sharpness(img).enhance(1.0 + sharpness_val)
        img = ImageEnhance.Contrast(img).enhance(1.15)

    if target_size:
        tw, th = target_size
        if blur_background:
            bg = img.copy().resize((tw, th), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (tw, th), (0, 0, 0, 50))
            bg = Image.alpha_composite(bg, dimmer)
        else:
            bg = Image.new("RGBA", target_size, (255, 255, 255, 255))
            
        fg = img.copy()
        fg.thumbnail((tw, th), Image.Resampling.LANCZOS)
        offset = ((tw - fg.size[0]) // 2, (th - fg.size[1]) // 2)
        bg.paste(fg, offset, fg)
        img = bg
    else:
        w, h = img.size
        if blur_background:
            bg = img.copy().filter(ImageFilter.GaussianBlur(radius=blur_intensity))
            dimmer = Image.new("RGBA", (w, h), (0, 0, 0, 50))
            bg = Image.alpha_composite(bg, dimmer)
            
            fg = img.copy()
            fg.thumbnail((int(w * 0.9), int(h * 0.9)), Image.Resampling.LANCZOS)
            offset = ((w - fg.size[0]) // 2, (h - fg.size[1]) // 2)
            bg.paste(fg, offset, fg)
            img = bg
        else:
            bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
            bg.paste(img, (0, 0), img)
            img = bg

    w, h = img.size

    if ensure_valid_image(config.ACTIVE_LOGO_PATH):
        try:
            logo = Image.open(config.ACTIVE_LOGO_PATH).convert("RGBA")
            if fit_auto_logo:
                logo.thumbnail((int(w * (logo_custom_w / 1000.0)), int(h * (logo_custom_h / 1000.0))), Image.Resampling.LANCZOS)
            else:
                logo = logo.resize((max(10, logo_custom_w), max(10, logo_custom_h)), Image.Resampling.LANCZOS)
                
            if remove_logo_bg:
                np_logo = np.array(logo)
                new_a = np.where((np_logo[:, :, 0] > 235) & (np_logo[:, :, 1] > 235) & (np_logo[:, :, 2] > 235), 0, np_logo[:, :, 3])
                logo.putalpha(Image.fromarray(new_a.astype('uint8')))

            r, g, b, a = logo.split()
            a = a.point(lambda p: int(p * opacity_val))
            logo_transparent = Image.merge("RGBA", (r, g, b, a))
            
            lx, ly = calculate_exact_position(w, h, logo.size[0], logo.size[1], logo_pos_mode, logo_off_x, logo_off_y)
            img.paste(logo_transparent, (lx, ly), logo_transparent)
        except Exception:
            pass

    base_brand_text = os.getenv("dynamic_brand_text", "Montgk Brand")
    calc_b_size = max(14, int(h * brand_text_scale))
    b_font = get_selected_font(font_choice, calc_b_size)
    if b_font:
        draw_single_custom_text(img, base_brand_text, b_font, hex_to_rgb(brand_color) + (255,), brand_pos, brand_off_x, brand_off_y)

    if extra_text.strip():
        calc_e_size = max(12, int(h * extra_text_scale))
        e_font = get_selected_font(font_choice, calc_e_size)
        if e_font:
            draw_single_custom_text(img, extra_text, e_font, hex_to_rgb(extra_color) + (255,), extra_pos, extra_off_x, extra_off_y)

    out_img_path = os.path.join(config.TMP_DIR, f"templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=int(quality_val))
    return out_img_path

def create_image_collage(image_paths, target_size=(1080, 1080)):
    num_images = len(image_paths)
    collage_img = Image.new('RGB', target_size, color=(255, 255, 255))
    
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

def extract_original_price_only(text, max_limit=None):
    clean_text = re.sub(r'01[0125]\d{8}', '', text)
    clean_text = re.sub(r'\d+\s*(?:شارع|طريق|ميدان|دور|شقة|مكرر)', '', clean_text)
    
    current_keywords = config.get_price_keywords()
    price_patterns = []
    for kw in current_keywords:
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

def generate_smart_ai_description(raw_text):
    clean = re.sub(r'http[s]?://\S+|www\.\S+', '', raw_text)
    clean = re.sub(r'#\w+', '', clean)
    clean = re.sub(r'01[0125]\d{8}', '', clean)
    words = [w for w in clean.split() if not w.isdigit()]
    base_description = " ".join(words[:20])
    return (
        f"🚨 **فرصة ذهبية لا تعوض - الكمية محدودة جداً!** 🚨\n"
        f"🔥 {base_description} 🔥\n"
        f"جودة عالية، تشطيب راقي، وتصميم يناسب كل احتياجاتك. جبناهالك بأقل سعر في السوق عشان تكسح منافسيك! 😉👑"
    )

def generate_auto_hashtags(product_name):
    clean_name = re.sub(r'[^\w\s]', '', product_name).strip().replace(" ", "_")
    base_tags = ["#عروض_مصر", "#تسوق_اونلاين", "#تخفيضات", "#منتجات_تريند", "#توصيل_سريع"]
    if clean_name: base_tags.insert(0, f"#{clean_name}")
    return " ".join(base_tags)

def send_telegram_post(bot_token, channel_username, text_message, image_url=None):
    if not bot_token or bot_token == "ضع_التوكن_الافتراضي_هنا":
        return False, "❌ توكن بوت تليجرام غير مسجل!"
    channel_target = channel_username if channel_username.startswith("@") else f"@{channel_username}"
    try:
        if image_url and image_url.startswith("http"):
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            payload = {"chat_id": channel_target, "photo": image_url, "caption": text_message, "parse_mode": "Markdown"}
            r = requests.post(url, data=payload, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": channel_target, "text": text_message, "parse_mode": "Markdown"}
            r = requests.post(url, data=payload, timeout=15)
        res_json = r.json()
        if res_json.get("ok"):
            return True, "✅ تم النشر بنجاح!"
        else:
            return False, f"❌ خطأ تليجرام: {res_json.get('description', 'غير معروف')}"
    except Exception as e:
        return False, f"❌ خطأ في الاتصال: {str(e)}"

# =========================================================
# واجهة التطبيق (Streamlit App)
# =========================================================
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
        <div class="banner-subtitle">{config.BRAND_NAME_AR} (Clean App Edition)</div>
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
    st.markdown("### 🔤 اختيار نوع الخط للكتابة")
    font_choice = st.selectbox("اختر الخط المفضل:", [
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
    
    remove_logo_bg = st.checkbox("🫥 إزالة الخلفية البيضاء للوجو تلقائياً", value=True, key="rem_bg_chk")
    
    c_lw, c_lh = st.columns(2)
    with c_lw: logo_w = st.slider("عرض اللوجو (px):", 10, 1000, 200, key="logo_w")
    with c_lh: logo_h = st.slider("ارتفاع اللوجو (px):", 10, 1000, 200, key="logo_h")

    if ensure_valid_image(config.ACTIVE_LOGO_PATH):
        try:
            st.image(config.ACTIVE_LOGO_PATH, caption="اللوجو النشط الحالي", width=100)
        except:
            pass
            
    uploaded_logo = st.file_uploader("تغيير اللوجو:", type=["png", "jpg", "jpeg"], key="logo_uploader_safe")
    if uploaded_logo is not None:
        bytes_data = uploaded_logo.getvalue()
        if len(bytes_data) > 0:
            with open(config.ACTIVE_LOGO_PATH, "wb") as f:
                f.write(bytes_data)
            st.success("✅ تم تحديث اللوجو بنجاح!")
            st.rerun()

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
    blur_bg_opt = st.checkbox("تفعيل خلفية Blur", value=True, key="blur_bg")
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

    audio_mode = st.radio("مصدر الصوت:", ["تراك المزيكا الحصري التلقائي", "رفع تراك أوديو MP3 مخصص من جهازك"])
    uploaded_custom_audio = st.file_uploader("ارفع الأوديو:", type=["mp3", "wav", "ogg"]) if audio_mode == "رفع تراك أوديو MP3 مخصص من جهازك" else None

tab1, tab2, tab3, tab4 = st.tabs([
    "🎬 تشفير وتقطيع ومونتاج الفيديو", 
    "🖼️ قالب ألبومات وصور المنتجات", 
    "🛰️ رادار القنوات والـ Forward",
    "🔥 رادار الترندات واسطمبة البوستات"
])

with tab1:
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
                
                if ensure_valid_image(config.ACTIVE_LOGO_PATH):
                    vx, vy = calculate_exact_position(modified_clip.w, modified_clip.h, logo_w, logo_h, logo_pos, logo_ox, logo_oy)
                    logo = (ImageClip(config.ACTIVE_LOGO_PATH)
                            .set_duration(modified_clip.duration)
                            .resize(newsize=(logo_w, logo_h))
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

with tab2:
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
                    
                    processed_p = process_image_template(
                        temp_p, blur_background=blur_bg_opt, blur_intensity=blur_intensity_val, opacity_val=logo_opacity,
                        fit_auto_logo=fit_auto_logo, logo_custom_w=logo_w, logo_custom_h=logo_h,
                        brand_text_scale=brand_sc, brand_color=brand_cl, brand_pos=brand_pos,
                        brand_off_x=brand_ox, brand_off_y=brand_oy, extra_text=extra_suffix,
                        extra_text_scale=extra_sc, extra_color=extra_cl, extra_pos=extra_pos,
                        extra_off_x=extra_ox, extra_off_y=extra_oy, target_size=chosen_size,
                        enhance_quality=enhance_quality_opt, sharpness_val=sharpness_slider_val, quality_val=quality_slider_val,
                        logo_pos_mode=logo_pos, logo_off_x=logo_ox, logo_off_y=logo_oy,
                        color_preset=color_preset, enable_crop=enable_crop_opt, c_left=crop_l, c_top=crop_t, c_right=crop_r, c_bottom=crop_b,
                        font_choice=font_choice, remove_logo_bg=remove_logo_bg
                    )
                    saved_paths.append(processed_p)
                    if os.path.exists(temp_p): os.remove(temp_p)
                
                if album_choice == "📥 ألبوم صور مفرودة منفصلة":
                    st.success("🎉 تمت المعالجة بنجاح!")
                    for idx, p in enumerate(saved_paths): st.image(p, caption=f"منتج {idx+1}", use_container_width=True)
                elif album_choice == "🖼️ تجميع في صورة واحدة (Collage)":
                    collage_result = create_image_collage(saved_paths, chosen_size if chosen_size else (1080, 1080))
                    st.image(collage_result, caption="صورة الكولاج", use_container_width=True)
                else:
                    dur = 3
                    with st.spinner("🎬 جاري رندرة السلايد شو..."):
                        img_clips = [ImageClip(p).set_duration(dur) for p in saved_paths]
                        v_slide = concat_videoclips(img_clips, method="compose")
                        v_slide_path = "slideshow_out.mp4"
                        v_slide.write_videofile(v_slide_path, codec="libx264", fps=24, preset="ultrafast")
                        st.video(v_slide_path)

with tab3:
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
                                auto_price, old_str = extract_original_price_only(p_text, max_limit=max_price)
                                temp_collected.append({"text": p_text, "image": photo_url, "auto_price": auto_price, "old_str": old_str})
                        st.session_state["cached_posts"] = temp_collected
                        st.success(f"🎯 تم قنص وتحليل {len(temp_collected)} بوست بذكاء!")
                except Exception as e: st.error(f"خطأ: {str(e)}")
    else:
        fwd_text = st.text_area("نص البوست:", key="fwd_t")
        fwd_img = st.file_uploader("الصورة:", key="fwd_img")
        if st.button("⚡ تحليل وتعديل فوراً", key="btn_man"):
            if fwd_text:
                auto_price, old_str = extract_original_price_only(fwd_text, max_limit=max_price)
                st.session_state["cached_posts"] = [{"text": fwd_text, "image": fwd_img, "auto_price": auto_price, "old_str": old_str}]

    if st.session_state["cached_posts"]:
        for idx, item in enumerate(st.session_state["cached_posts"]):
            st.markdown(f"#### 📦 منتج رقم {idx + 1}")
            if item["image"]: st.image(item["image"], width=250)
            orig_p = st.number_input(f"السعر الأصلي المكتشف {idx+1}:", min_value=0, value=int(item["auto_price"]), key=f"orig_p_{idx}")
            new_p = int(orig_p * (1 + (price_inc_rate / 100)))
            
            profit_margin = new_p - orig_p
            st.success(f"💵 **حاسبة الأرباح الذكية:** المكسب المتوقع في القطعة الواحدة = **{profit_margin} جنيه** (بنسبة زيادة {price_inc_rate}%)")
            
            smart_desc = generate_smart_ai_description(item["text"])
            auto_tags = generate_auto_hashtags(item["text"][:15])
            
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
                    ok, msg = send_telegram_post(config.TELEGRAM_BOT_TOKEN, pub_ch, post_content, img_s)
                    if ok: st.success(msg)
                    else: st.error(msg)
            st.markdown("---")

with tab4:
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

st.markdown(f"<br><p style='text-align: center; color: #2a4d69; font-weight: bold;'>{config.DEVELOPER_SIGNATURE}</p>", unsafe_allow_html=True)
