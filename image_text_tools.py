import io
from PIL import Image, ImageFilter, ImageOps

def cleanup_text_from_image(file_bytes):
    """Best-effort cleanup for images with embedded text."""
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    except Exception:
        return None

    width, height = image.size
    if width == 0 or height == 0:
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
