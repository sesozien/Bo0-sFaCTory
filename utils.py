import os
import re
import hashlib
import requests
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance, ImageOps
import arabic_reshaper
from bidi.algorithm import get_display
import config

def ensure_valid_image(image_path):
    if not os.path.exists(image_path):
        return False
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def remove_logo_background(logo, threshold=235):
    """Remove only near-white pixels connected to the logo edges.

    This preserves white text, crowns, borders, and other white details inside
    the logo instead of deleting every white pixel globally.
    """
    rgba = np.array(logo.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3].copy()
    near_white = np.all(rgb >= threshold, axis=2)
    height, width = near_white.shape
    visited = np.zeros_like(near_white, dtype=bool)
    stack = []
    for x in range(width):
        if near_white[0, x]: stack.append((0, x))
        if height > 1 and near_white[height - 1, x]: stack.append((height - 1, x))
    for y in range(height):
        if near_white[y, 0]: stack.append((y, 0))
        if width > 1 and near_white[y, width - 1]: stack.append((y, width - 1))

    while stack:
        y, x = stack.pop()
        if y < 0 or y >= height or x < 0 or x >= width or visited[y, x] or not near_white[y, x]:
            continue
        visited[y, x] = True
        alpha[y, x] = 0
        stack.extend(((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))

    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")

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
                           enable_watermark_pattern=False, color_preset="طبيعي (بدون فلتر)",
                           enable_crop=False, c_left=0, c_top=0, c_right=0, c_bottom=0, font_choice="Cairo (عربي عريض فاخر)", remove_logo_bg=True):
    
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
            offset = ((w - fg.size[0]) // 2, (th - fg.size[1]) // 2)
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
                logo = remove_logo_background(logo)

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

def supplier_code(channel_name):
    """Create a short code from the channel name for the final post."""
    name = re.sub(r"^@", "", str(channel_name or "")).strip()
    name = re.sub(r"^ال", "", name)
    letters = re.findall(r"[A-Za-z\u0621-\u064A]", name)
    return "".join(letters[:2]).upper() or "NA"


def normalize_product_text(text):
    clean = re.sub(r"https?://\S+|www\.\S+", " ", text or "")
    clean = re.sub(r"#\S+|@\S+", " ", clean)
    clean = re.sub(r"01[0125]\d{8}", " ", clean)
    clean = re.sub(r"(?:سعر|السعر|جنيه|جنية|ج)\s*[:\-]?\s*\d+", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\d+\s*(?:جنيه|جنية|ج)", " ", clean, flags=re.IGNORECASE)
    return " ".join(clean.split()).casefold()


def product_identity(text, image_url=None):
    image_name = ""
    if image_url:
        image_name = str(image_url).split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1].casefold()
    raw = f"{normalize_product_text(text)}|{image_name}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def compare_products(posts, channel_name, index=None):
    """Compare identical description/image products seen across radar fetches."""
    index = index if index is not None else {}
    code = supplier_code(channel_name)
    for item in posts:
        item["source_channel"] = channel_name
        item["source_code"] = code
        key = product_identity(item.get("text", ""), item.get("image"))
        item["comparison_key"] = key
        previous = index.get(key)
        item["comparison"] = None
        current_price = int(item.get("auto_price") or 0)
        if previous and previous.get("channel") != channel_name:
            old_price = int(previous.get("price") or 0)
            if current_price and old_price and old_price < current_price:
                item["comparison"] = {"type": "cheaper", "price": old_price, "code": previous.get("code", "NA"), "channel": previous.get("channel", "")}
            elif current_price and old_price and current_price < old_price:
                item["comparison"] = {"type": "current_cheaper", "price": current_price, "code": code, "channel": channel_name}
            elif current_price and old_price == current_price:
                item["comparison"] = {"type": "same_price", "price": current_price, "code": previous.get("code", "NA"), "channel": previous.get("channel", "")}
        if not previous or current_price and current_price < int(previous.get("price") or 0):
            index[key] = {"price": current_price, "code": code, "channel": channel_name, "text": item.get("text", "")}
    return posts


def clean_product_text(text, source_channel=None):
    clean = re.sub(r"https?://\S+|www\.\S+", "", text or "")
    clean = re.sub(r"#\S+", "", clean)
    clean = re.sub(r"01[0125]\d{8}", "", clean)
    if source_channel:
        clean = re.sub(rf"@?{re.escape(source_channel)}", "", clean, flags=re.IGNORECASE)
    clean = " ".join(clean.split()).strip()
    return f"{clean}\n\nMr :- Bo0" if clean else "Mr :- Bo0"


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
