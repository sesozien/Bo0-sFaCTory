import os
import re
import hashlib
import base64
import xml.etree.ElementTree as ET
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

def _contains_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def get_selected_font(font_choice, font_size=24, text=""):
    """Load a real Arabic-capable font from the repository before any fallback."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    local_fonts = {
        "Cairo (عربي عريض فاخر)": os.path.join(project_dir, "Cairo", "static", "Cairo-Bold.ttf"),
        "Tajawal (عربي أنيق وانسيابي)": os.path.join(project_dir, "Cairo", "static", "Cairo-Bold.ttf"),
        "Amiri (عربي كلاسيكي أصيل)": os.path.join(project_dir, "Cairo", "static", "Cairo-Bold.ttf"),
    }
    font_urls = {
        "Roboto (إنجليزي مودرن وسريع)": "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Bold.ttf",
        "Montserrat (إنجليزي عريض وبارز)": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf",
    }
    # Any Arabic text must use the checked-in Cairo font, even if the user selected an English font.
    if _contains_arabic(text) or font_choice in local_fonts:
        font_path = local_fonts["Cairo (عربي عريض فاخر)"]
    else:
        font_path = local_fonts.get(font_choice)
        if not font_path:
            font_dir = os.path.join(os.path.expanduser("~"), ".fonts")
            os.makedirs(font_dir, exist_ok=True)
            font_path = os.path.join(font_dir, font_choice.split()[0] + "-Bold.ttf")
            if not os.path.exists(font_path) and font_choice in font_urls:
                try:
                    response = requests.get(font_urls[font_choice], timeout=15)
                    response.raise_for_status()
                    with open(font_path, "wb") as stream:
                        stream.write(response.content)
                except (OSError, requests.RequestException):
                    pass
    try:
        return ImageFont.truetype(font_path, font_size)
    except (OSError, TypeError):
        cairo_path = local_fonts["Cairo (عربي عريض فاخر)"]
        try:
            return ImageFont.truetype(cairo_path, font_size)
        except (OSError, TypeError):
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

def choose_smart_logo_position(image, logo_size, margin=15):
    """Choose the least visually busy corner for the logo."""
    rgba = image.convert("RGB")
    width, height = rgba.size
    logo_w, logo_h = logo_size
    candidates = {
        "فوق يمين (Top-Right)": (max(0, width - logo_w - margin), margin),
        "فوق شمال (Top-Left)": (margin, margin),
        "تحت يمين (Bottom-Right)": (max(0, width - logo_w - margin), max(0, height - logo_h - margin)),
        "تحت شمال (Bottom-Left)": (margin, max(0, height - logo_h - margin)),
    }
    scores = {}
    for name, (x, y) in candidates.items():
        patch = np.asarray(rgba.crop((x, y, min(width, x + logo_w), min(height, y + logo_h))), dtype=np.float32)
        scores[name] = float(patch.std()) if patch.size else float("inf")
    return min(scores, key=scores.get)


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
                           enable_crop=False, c_left=0, c_top=0, c_right=0, c_bottom=0, font_choice="Cairo (عربي عريض فاخر)", remove_logo_bg=True, smart_logo_position=False):
    
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
                logo = remove_logo_background(logo)

            r, g, b, a = logo.split()
            a = a.point(lambda p: int(p * opacity_val))
            logo_transparent = Image.merge("RGBA", (r, g, b, a))
            
            effective_logo_pos = choose_smart_logo_position(img, logo.size) if smart_logo_position else logo_pos_mode
            lx, ly = calculate_exact_position(w, h, logo.size[0], logo.size[1], effective_logo_pos, logo_off_x, logo_off_y)
            img.paste(logo_transparent, (lx, ly), logo_transparent)
        except Exception:
            pass

    base_brand_text = os.getenv("dynamic_brand_text", "Montgk Brand")
    calc_b_size = max(14, int(h * brand_text_scale))
    b_font = get_selected_font(font_choice, calc_b_size, base_brand_text)
    if b_font:
        draw_single_custom_text(img, base_brand_text, b_font, hex_to_rgb(brand_color) + (255,), brand_pos, brand_off_x, brand_off_y)

    if extra_text.strip():
        calc_e_size = max(12, int(h * extra_text_scale))
        e_font = get_selected_font(font_choice, calc_e_size, extra_text)
        if e_font:
            draw_single_custom_text(img, extra_text, e_font, hex_to_rgb(extra_color) + (255,), extra_pos, extra_off_x, extra_off_y)

    out_img_path = os.path.join(config.TMP_DIR, f"templated_{os.path.basename(image_path)}")
    img.convert("RGB").save(out_img_path, "JPEG", quality=int(quality_val))
    return out_img_path

def create_image_collage(image_paths, target_size=(1080, 1080), output_name='montgk_collage_output.jpg'):
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
        
    out_collage_path = os.path.join(config.TMP_DIR, output_name)
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


def round_price_to_five(value):
    """Round to the nearest 5; a remainder up to 2.5 rounds down."""
    value = float(value or 0)
    if value <= 0:
        return 0
    lower = int(value // 5) * 5
    remainder = value - lower
    return lower if remainder <= 2.5 else lower + 5


def apply_profit_margin(original_price, profit_percent=35, rounding=True):
    price = float(original_price or 0) * (1 + float(profit_percent or 0) / 100)
    return int(round_price_to_five(price) if rounding else round(price))


def _telegram_photo_urls(message):
    """Return every photo URL attached to one public Telegram message/album."""
    urls = []
    for photo_tag in message.find_all('a', {'class': 'tgme_widget_message_photo_wrap'}):
        style = photo_tag.get('style', '')
        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
        if not match:
            continue
        url = match.group(1)
        url = 'https:' + url if url.startswith('//') else url
        if url not in urls:
            urls.append(url)
    return urls


def _telegram_photo_url(message):
    urls = _telegram_photo_urls(message)
    return urls[0] if urls else None


def _strip_price_mentions(text):
    """Remove supplier prices so no original price leaks into title or description."""
    text = text or ''
    patterns = [
        r'(?:السعر|سعر|price)\s*[:：=\-]?\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:جنيه|جنية|ج)?',
        r'\d+(?:\s*[-–]\s*\d+)?\s*(?:جنيه|جنية|ج)\b',
    ]
    for pattern in patterns:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    return re.sub(r'\s*[,،;؛|—–-]\s*', ' ', text)


def remove_original_prices(text):
    """Public wrapper used to migrate products created by older app versions."""
    return _strip_price_mentions(text)


def _make_remote_collage(urls, identity):
    """Download album images once and create one local collage for preview/export."""
    local_paths = []
    for index, url in enumerate(urls[:9]):
        try:
            if os.path.exists(str(url)):
                path = str(url)
            else:
                response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
                response.raise_for_status()
                path = os.path.join(config.TMP_DIR, f'album_{identity}_{index}.jpg')
                with open(path, 'wb') as stream:
                    stream.write(response.content)
            with Image.open(path) as image:
                image.verify()
            local_paths.append(path)
        except (requests.RequestException, OSError, ValueError):
            continue
    if len(local_paths) < 2:
        return local_paths[0] if local_paths else (urls[0] if urls else '')
    return create_image_collage(local_paths, target_size=(1080, 1080), output_name=f'album_{identity}_collage.jpg')

def _has_explicit_price(text):
    text = text or ''
    return bool(re.search(r'(?:السعر|سعر|price|جنيه|جنية|EGP|LE|ج\b)\s*[:：=\-]?\s*\d+|\d+\s*(?:جنيه|جنية|ج\b|EGP|LE)', text, re.IGNORECASE))


def fetch_public_channel_messages(channel, date_from=None, marker_text='', max_messages=100, max_pages=5, allowed_forwarders=None, exclude_forwarded=True):
    """Fetch a bounded batch from a public t.me channel only when the user clicks scan."""
    channel = str(channel or '').strip().lstrip('@').split('/')[-1]
    if not channel:
        return []
    collected = []
    before = None
    marker = (marker_text or '').casefold().strip()
    allowed = {str(name).strip().casefold() for name in (allowed_forwarders or []) if str(name).strip()}
    for _ in range(max_pages):
        url = f'https://t.me/s/{channel}' + (f'?before={before}' if before else '')
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser') if 'BeautifulSoup' in globals() else None
        if soup is None:
            from bs4 import BeautifulSoup as _Soup
            soup = _Soup(response.content, 'html.parser')
        wraps = soup.find_all('div', class_=lambda value: value and 'tgme_widget_message_wrap' in value)
        if not wraps:
            break
        page_ids = []
        stop = False
        for wrap in wraps:
            message = wrap.find('div', class_=lambda value: value and 'tgme_widget_message' in value)
            text_div = wrap.find('div', {'class': 'tgme_widget_message_text'})
            text = text_div.get_text(' ', strip=True) if text_div else ''
            forwarded_block = wrap.select_one('.tgme_widget_message_forwarded_from')
            forwarded_tag = wrap.select_one('.tgme_widget_message_forwarded_from_name')
            forwarded_name = forwarded_tag.get_text(' ', strip=True) if forwarded_tag else ''
            is_forwarded = forwarded_block is not None
            date_tag = wrap.find('time')
            date_value = date_tag.get('datetime', '') if date_tag else ''
            link_tag = wrap.find('a', {'class': 'tgme_widget_message_date'})
            source_url = link_tag.get('href', '') if link_tag else ''
            message_id = ''
            data_post = message.get('data-post', '') if message else ''
            if data_post:
                message_id = data_post.rsplit('/', 1)[-1]
            if message_id:
                page_ids.append(int(message_id) if message_id.isdigit() else message_id)
            if date_from and date_value and date_value[:10] < str(date_from):
                stop = True
                continue
            if marker and marker in text.casefold():
                stop = True
                continue
            photo_urls = _telegram_photo_urls(wrap)
            if not text and not photo_urls:
                continue
            # Only accept real product posts: an image and an explicit price.
            # Forwarded advertising is accepted only when its source name is allowed.
            if not photo_urls or not _has_explicit_price(text):
                continue
            if exclude_forwarded and is_forwarded and not (forwarded_name and any(name in forwarded_name.casefold() for name in allowed)):
                continue
            price, old_str = extract_original_price_only(text)
            collected.append({
                'text': text,
                'image': photo_urls[0] if photo_urls else None,
                'images': photo_urls,
                'source_url': source_url,
                'message_id': message_id,
                'date': date_value,
                'auto_price': price,
                'old_str': old_str,
                'source_channel': channel,
                'forwarded_from': forwarded_name,
            })
            if len(collected) >= int(max_messages):
                break
        if len(collected) >= int(max_messages) or stop or not page_ids:
            break
        before = min(page_ids)
    collected.sort(key=lambda item: item.get('date', ''))
    return collected[:int(max_messages)]


def extract_product_attributes(text):
    """Best-effort extraction; the user can edit every field before export."""
    text = text or ''
    sizes = re.findall(r'(?i)\\b(?:XS|S|M|L|XL|XXL|XXXL|3XL|4XL)\\b', text)
    colors = []
    color_words = ['اسود', 'أبيض', 'ابيض', 'رمادي', 'بيج', 'احمر', 'أحمر', 'نبيتي', 'روز', 'فوشيا', 'مينت', 'بيبي بلو', 'اخضر', 'أخضر', 'اورانج', 'برتقالي', 'كاشمير', 'هافان', 'تفاحي', 'اصفر', 'أصفر', 'زيتي', 'كحلي', 'لافندر', 'بني', 'اسود/ابيض']
    low = text.casefold()
    for color in color_words:
        if color.casefold() in low and color not in colors:
            colors.append(color)
    material_match = re.search(r'(?:خامة|خامه|قماش|نوع القماش)\\s*[:：-]?\\s*([^\\n،,]+)', text, re.IGNORECASE)
    material = material_match.group(1).strip() if material_match else ''
    title_line = next((line.strip() for line in text.splitlines() if line.strip()), 'منتج جديد')
    title_line = re.sub(r'https?://\\S+|#\\S+|@[\\w_]+', '', title_line).strip()
    title_line = _strip_price_mentions(title_line).strip()
    return {'title': title_line[:120] or 'منتج جديد', 'sizes': '، '.join(dict.fromkeys(sizes)), 'colors': '، '.join(colors), 'material': material}


def build_catalog_product(item, profit_percent=35, rounding=True, brand='Bo0'):
    original = float(item.get('auto_price') or 0)
    attrs = extract_product_attributes(item.get('text', ''))
    image_sources = item.get('images') or ([item.get('image')] if item.get('image') else [])
    product_id = product_identity(item.get('text', ''), '|'.join(image_sources))
    image_value = _make_remote_collage(image_sources, product_id) if len(image_sources) > 1 else (image_sources[0] if image_sources else '')
    final_price = apply_profit_margin(original, profit_percent, rounding) if original else 0
    description_parts = [part for part in [
        f"المقاسات: {attrs['sizes']}" if attrs['sizes'] else '',
        f"الألوان: {attrs['colors']}" if attrs['colors'] else '',
        f"الخامة: {attrs['material']}" if attrs['material'] else '',
        clean_product_text(_strip_price_mentions(item.get('text', '')), item.get('source_channel')),
    ] if part]
    return {
        'id': product_id,
        'title': attrs['title'],
        'description': '\n'.join(description_parts),
        'availability': 'in stock',
        'condition': 'new',
        'price': final_price,
        'currency': 'EGP',
        'original_price': int(original),
        'profit_percent': float(profit_percent),
        'image_link': image_value,
        'link': item.get('source_url', ''),
        'brand': brand,
        'source_channel': item.get('source_channel', ''),
        'source_date': item.get('date', ''),
        'approved': False,
        'source_text': item.get('text', ''),
    }


def make_catalog_csv(products):
    import csv
    import io
    fields = ['id', 'title', 'description', 'availability', 'condition', 'price', 'currency', 'image_link', 'link', 'brand']
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(products)
    return out.getvalue().encode('utf-8-sig')


def make_catalog_zip(products):
    import io
    import zipfile
    from pathlib import Path
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('catalog.csv', make_catalog_csv(products))
        zf.writestr('catalog.json', __import__('json').dumps(products, ensure_ascii=False, indent=2))
        for index, product in enumerate(products, start=1):
            image_url = product.get('image_link')
            if not image_url:
                continue
            try:
                if os.path.exists(str(image_url)):
                    with open(image_url, 'rb') as stream:
                        zf.writestr(f'images/{product["id"]}_{index}.jpg', stream.read())
                else:
                    response = requests.get(image_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
                    response.raise_for_status()
                    zf.writestr(f'images/{product["id"]}_{index}.jpg', response.content)
            except (requests.RequestException, OSError):
                continue
    return archive.getvalue()

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

def get_trending_hashtags(limit=8):
    """Read current Egypt Google Trends titles; keep a safe fallback if unavailable."""
    fallback = ["#عروض_مصر", "#ترند", "#تسوق_اونلاين", "#منتجات_تريند", "#خصومات"]
    try:
        response = requests.get("https://trends.google.com/trending/rss?geo=EG", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        titles = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            if title:
                tag = "#" + re.sub(r"[^\w\u0600-\u06FF]+", "_", title).strip("_")
                if len(tag) > 1 and tag not in titles:
                    titles.append(tag)
            if len(titles) >= limit:
                break
        return titles[:limit] or fallback
    except (requests.RequestException, ET.ParseError, ValueError):
        return fallback


def generate_auto_hashtags(product_name, extra_hashtags=None):
    clean_name = re.sub(r"[^\w\u0600-\u06FF\s]", "", product_name or "").strip().replace(" ", "_")
    base_tags = list(extra_hashtags or ["#عروض_مصر", "#تسوق_اونلاين", "#تخفيضات", "#منتجات_تريند", "#توصيل_سريع"])
    if clean_name:
        base_tags.insert(0, f"#{clean_name}")
    return " ".join(dict.fromkeys(base_tags))


def generate_product_ad(image_bytes, manual_template="", extra_details="", hashtags=None):
    """Generate Arabic product copy from an image when a vision key is configured.

    Without a key, return a useful template-based ad instead of failing the app.
    """
    tags = generate_auto_hashtags(extra_details or "منتج", hashtags)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key and image_bytes:
        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
            prompt = ("اكتب إعلانًا مصريًا جذابًا بالعربية لهذا المنتج. اقرأ تفاصيل الصورة بدون اختراع مواصفات غير واضحة. "
                      "استخدم القالب اليدوي إن وُجد، واجعل النص مناسبًا لمنشور بيع قصير مع عنوان وفوائد ودعوة للشراء. "
                      f"تفاصيل يدوية: {extra_details or 'لا توجد'}\nالقالب اليدوي: {manual_template or 'اكتب بأسلوبك'}")
            payload = {"model": os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"), "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]}], "max_tokens": 500}
            response = requests.post(f"{base_url}/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=45)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"].strip()
            return f"{text}\n\n{tags}", True
        except (requests.RequestException, KeyError, TypeError, ValueError):
            pass
    title = extra_details.strip() or "منتج مميز"
    template = manual_template.strip() or "🔥 {المنتج}\n\nجودة ممتازة وشكل عملي يناسب استخدامك اليومي.\nللطلب والاستفسار تواصل معنا الآن."
    text = template.replace("{المنتج}", title)
    return f"{text}\n\n{tags}\n\nMr :- Bo0", False


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
