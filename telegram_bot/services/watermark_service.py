"""
watermark_service.py
Adds a text or logo watermark to the bottom-right corner of an image.
"""

import logging
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import WATERMARK_TEXT, WATERMARK_LOGO

logger = logging.getLogger(__name__)

# Tweak these to your taste
PADDING        = 18    # px from edge
FONT_SIZE      = 36    # for text watermark
TEXT_OPACITY   = 200   # 0-255
SHADOW_OPACITY = 120
LOGO_MAX_W     = 200   # max logo width in px


def apply_watermark(image_bytes: bytes) -> bytes:
    """
    Takes raw image bytes, returns watermarked image bytes (PNG).
    Uses a logo if WATERMARK_LOGO path is set, otherwise text.
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")

    if WATERMARK_LOGO and Path(WATERMARK_LOGO).exists():
        img = _add_logo_watermark(img)
    else:
        img = _add_text_watermark(img)

    output = BytesIO()
    img.convert("RGB").save(output, format="JPEG", quality=92)
    return output.getvalue()


# ── Text watermark ────────────────────────────────────────────────────────────

def _add_text_watermark(img: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    font = _load_font(FONT_SIZE)
    text = WATERMARK_TEXT

    # Measure text
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]

    x = img.width  - tw - PADDING
    y = img.height - th - PADDING

    # Drop shadow
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, SHADOW_OPACITY))
    # White text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, TEXT_OPACITY))

    return Image.alpha_composite(img, overlay)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    logger.warning("No TrueType font found, using default bitmap font")
    return ImageFont.load_default()


# ── Logo watermark ────────────────────────────────────────────────────────────

def _add_logo_watermark(img: Image.Image) -> Image.Image:
    logo = Image.open(WATERMARK_LOGO).convert("RGBA")

    # Scale logo proportionally
    ratio = LOGO_MAX_W / logo.width
    new_w = int(logo.width  * ratio)
    new_h = int(logo.height * ratio)
    logo  = logo.resize((new_w, new_h), Image.LANCZOS)

    # Make it semi-transparent
    r, g, b, a = logo.split()
    a = a.point(lambda x: int(x * 0.75))
    logo.putalpha(a)

    x = img.width  - new_w - PADDING
    y = img.height - new_h - PADDING

    img.paste(logo, (x, y), mask=logo)
    return img
