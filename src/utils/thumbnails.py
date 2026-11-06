"""
Page previews for the Rotate screen.

If PyMuPDF is installed (`pip install pymupdf`) the real page content is shown.
Otherwise a simple drawn page is shown, with the right proportions and
"text lines" at the top, so you can still see which way is up.
"""
from PIL import Image, ImageDraw
from pypdf import PdfReader

try:
    import pymupdf
except ImportError:
    pymupdf = None


THUMB_SIZE = 280  # longest side in pixels (rendered at 2x for sharp display)
PREVIEW_BG = "#F2F6FC"  # background behind the preview in the app


def has_real_previews():
    return pymupdf is not None


def page_thumbnails(pdf_path):
    """Return a list of PIL images, one per page, in the current orientation."""
    if pymupdf is not None:
        try:
            return _rendered_thumbnails(pdf_path)
        except Exception:
            pass  # fall back to drawn pages
    return _drawn_thumbnails(pdf_path)


def _rendered_thumbnails(pdf_path):
    images = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            zoom = THUMB_SIZE / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return images


def _drawn_thumbnails(pdf_path):
    reader = PdfReader(pdf_path)
    images = []
    for page in reader.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if (page.rotation or 0) % 180 == 90:
            width, height = height, width
        images.append(_draw_page(width, height))
    return images


def _draw_page(width, height):
    scale = THUMB_SIZE / max(width, height)
    w, h = max(int(width * scale), 40), max(int(height * scale), 40)

    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline="#C9D3E3", width=2)

    margin = int(min(w, h) * 0.12)
    line_h = max(int(min(w, h) * 0.035), 4)
    gap = line_h * 2

    # A "title" bar plus some text lines in the top part, so "up" is visible.
    draw.rectangle([margin, margin, int(w * 0.6), margin + line_h * 2], fill="#00843D")
    y = margin + line_h * 2 + gap
    widths = [0.88, 0.8, 0.86, 0.6, 0.84, 0.72]
    for frac in widths:
        if y + line_h > h * 0.62:
            break
        draw.rectangle([margin, y, margin + int((w - 2 * margin) * frac), y + line_h], fill="#D5DCE8")
        y += gap

    # Folded corner top-right
    fold = int(min(w, h) * 0.14)
    draw.polygon([(w - fold, 0), (w - 1, fold), (w - fold, fold)], fill="#E5ECF7", outline="#C9D3E3")
    draw.polygon([(w - fold, 0), (w, 0), (w, fold)], fill=PREVIEW_BG)
    return img
