"""
Make all PLOOI logo files from the design in images/logo/plooi-design.json.

    .venv\\Scripts\\python.exe tools\\make_logo.py

The design: heavy letters cut into pieces by thin white lines (same style as
the KUNSD logo). The JSON holds every piece, colour and cut, so the logo can be
drawn at any size. This script writes:

    images/logo/plooi-logo.svg / .png      the word PLOOI
    images/logo/plooi-icon.svg / .png      the P on a cream rounded square
    images/logo/plooi.ico                  window, taskbar and .exe icon (16-256 px)
    images/splash.png                      start screen of the .exe
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LOGO_DIR = ROOT / "images" / "logo"
DESIGN = json.loads((LOGO_DIR / "plooi-design.json").read_text(encoding="utf-8"))

CREAM = "#fbf9f4"
INK = "#171717"
MUTED = "#6B6B6B"
BLUE = "#2b59c3"
H = DESIGN["height"]
CUT = DESIGN["cut_width"]


# ---------- drawing ----------

def draw(letters, width, height_px, ss=4, min_cut_px=0.0):
    """The letters as a transparent PNG, height_px high."""
    scale = height_px / H * ss
    size = (int(width * scale) + 1, int(H * scale) + 1)
    colour = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)
    dc, dm = ImageDraw.Draw(colour), ImageDraw.Draw(mask)
    cut = max(CUT * scale, min_cut_px * ss)

    def tr(points, ox):
        return [((x + ox) * scale, y * scale) for x, y in points]

    for letter in letters:
        ox = letter["x"]
        for piece in letter["pieces"]:
            dc.polygon(tr(piece["points"], ox), fill=piece["fill"])
        for a, b in letter["cuts"]:
            dc.line(tr([a, b], ox), fill="white", width=max(1, round(cut)))
        for shape in letter["shapes"]:
            dm.polygon(tr(shape["outer"], ox), fill=255)
        for shape in letter["shapes"]:
            for hole in shape["holes"]:
                dm.polygon(tr(hole, ox), fill=0)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(colour, (0, 0), mask)
    return out.resize((size[0] // ss, size[1] // ss), Image.LANCZOS)


def svg_group(letters, uid):
    def path(points, ox=0):
        return "M" + "L".join(f"{x + ox:g},{y:g}" for x, y in points) + "Z"

    parts = []
    for i, letter in enumerate(letters):
        clip = "".join(
            f'<path fill-rule="evenodd" clip-rule="evenodd" d="{path(s["outer"])}{"".join(path(h) for h in s["holes"])}"/>'
            for s in letter["shapes"])
        pieces = "".join(f'<path d="{path(p["points"])}" fill="{p["fill"]}"/>' for p in letter["pieces"])
        cuts = "".join(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#fff" stroke-width="{CUT}"/>'
                       for a, b in letter["cuts"])
        parts.append(f'<g transform="translate({letter["x"]},0)"><clipPath id="{uid}{i}">{clip}</clipPath>'
                     f'<g clip-path="url(#{uid}{i})">{pieces}{cuts}</g></g>')
    return "".join(parts)


# ---------- icon (P on a cream square, like the KUNSD favicon) ----------

P = dict(DESIGN["letters"][0], x=0)
P_WIDTH = P["width"]
ICON_FILL = 0.76   # part of the square the P takes


def icon_png(size):
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * 0.22), fill=CREAM)
    img = img.resize((size, size), Image.LANCZOS)
    letter_h = ICON_FILL * size * H / max(P_WIDTH, H)
    # small icons: keep the white cuts at least ~0.8 px so they stay visible
    mark = draw([P], P_WIDTH, letter_h, min_cut_px=0.8 if size <= 48 else 0)
    img.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2))
    return img


def icon_svg(size=121):
    scale = ICON_FILL * size / max(P_WIDTH, H)
    w, h = P_WIDTH * scale, H * scale
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{size * 0.22:.1f}" fill="{CREAM}"/>'
            f'<g transform="translate({(size - w) / 2:.2f},{(size - h) / 2:.2f}) scale({scale:.4f})">'
            f'{svg_group([P], "p")}</g></svg>')


# ---------- splash screen ----------

def splash():
    W, Hs = 560, 250
    img = Image.new("RGBA", (W, Hs), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, Hs - 1], outline="#E5E1D8", width=2)
    # thin stripe in the four logo colours at the bottom
    for i, colour in enumerate([INK, "#e9a80c", "#d7263d", BLUE]):
        d.rectangle([i * W // 4, Hs - 8, (i + 1) * W // 4, Hs], fill=colour)
    mark = draw(DESIGN["letters"], DESIGN["width"], 46)
    img.alpha_composite(mark, ((W - mark.width) // 2, 64))
    font_path = "C:/Windows/Fonts/bahnschrift.ttf"
    small = ImageFont.truetype(font_path, 16)
    small.set_variation_by_name("Light")
    for text, y, colour in (("PDF tools  ·  by Jesse Metz", 150, MUTED), ("Starting…", 190, BLUE)):
        d.text(((W - d.textlength(text, font=small)) / 2, y), text, font=small, fill=colour)
    return img.convert("RGB")


if __name__ == "__main__":
    letters, width = DESIGN["letters"], DESIGN["width"]
    (LOGO_DIR / "plooi-logo.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {H}" role="img" aria-label="PLOOI">'
        f'<title>PLOOI</title>{svg_group(letters, "l")}</svg>', encoding="utf-8")
    draw(letters, width, 160).save(LOGO_DIR / "plooi-logo.png")
    (LOGO_DIR / "plooi-icon.svg").write_text(icon_svg(), encoding="utf-8")
    icon_png(256).save(LOGO_DIR / "plooi-icon.png")

    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    images = [icon_png(s) for s in sizes]
    images[-1].save(LOGO_DIR / "plooi.ico", format="ICO", sizes=[(s, s) for s in sizes],
                    append_images=images[:-1])
    splash().save(ROOT / "images" / "splash.png")
    print("Logo files written to", LOGO_DIR)
