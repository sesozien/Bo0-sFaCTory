import io

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps


def extract_product_from_image(file_bytes, left, top, right, bottom):
    """Extract the product inside a user-selected rectangle as a transparent PNG."""
    try:
        source = np.frombuffer(file_bytes, dtype=np.uint8)
        image = cv2.imdecode(source, cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return None
        height, width = image.shape[:2]
        left = max(0, min(int(left), width - 2))
        top = max(0, min(int(top), height - 2))
        right = max(left + 2, min(int(right), width))
        bottom = max(top + 2, min(int(bottom), height))
        rect = (left, top, right - left, bottom - top)
        mask = np.zeros((height, width), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 6, cv2.GC_INIT_WITH_RECT)
        foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = foreground
        cropped = rgba[top:bottom, left:right]
        ok, encoded = cv2.imencode(".png", cropped)
        return encoded.tobytes() if ok else None
    except Exception:
        return None


def remove_text_from_image(file_bytes):
    """Remove high-contrast text approximately with OpenCV inpainting.

    This works best for dark/light text over a mostly smooth background. It
    returns a new PNG and never mutates the uploaded image.
    """
    try:
        source = np.frombuffer(file_bytes, dtype=np.uint8)
        image = cv2.imdecode(source, cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blackhat_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, blackhat_kernel)
        _, dark_mask = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        whitehat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, blackhat_kernel)
        _, light_mask = cv2.threshold(whitehat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = cv2.bitwise_or(dark_mask, light_mask)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        result = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
        ok, encoded = cv2.imencode(".png", result)
        return encoded.tobytes() if ok else None
    except Exception:
        return None


def cleanup_text_from_image(file_bytes):
    """Create a contrast-enhanced grayscale copy for reading text.

    This is enhancement, not text deletion; use remove_text_from_image for
    an inpainted copy.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    except Exception:
        return None
    if image.width == 0 or image.height == 0:
        return None
    gray = ImageOps.grayscale(image)
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=2))
    contrast = ImageOps.autocontrast(blurred)
    buf = io.BytesIO()
    contrast.save(buf, format="PNG")
    return buf.getvalue()


def generate_product_ad_with_secrets(image_bytes, ad_template, ad_details, tags):
    """Fallback local ad generation without touching legacy app logic."""
    details = (ad_details or "").strip()
    template = (ad_template or "{المنتج} — جودة عالية، اطلب الآن!").strip()
    product_name = details or "المنتج"
    generated = template.format(المنتج=product_name)
    if tags:
        generated = generated + "\n\n" + " ".join(tags[:8])
    return generated, False
