import io
import re
from pathlib import Path

from PIL import Image, ImageOps
from pypdf import PdfWriter


# Image types that can be converted to PDF.
#  - Photos, scans and screenshots: jpg/jpeg/jfif, png, bmp, tif/tiff, webp, avif
#  - gif: only the first frame is used (animations can't live in a PDF)
#  - Multi-page tif files become multiple PDF pages
# Not accepted: svg (vector, Pillow can't read it), heic (iPhone photos, needs an
# extra package), psd/raw camera files and ico (icons), which rarely make sense as PDF.
IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".jfif", ".png", ".bmp",
    ".gif", ".tif", ".tiff", ".webp", ".avif",
)

A4_LONG_SIDE_INCH = 11.69
JPEG_QUALITY = 95


def is_image_file(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def load_frames(image_path):
    """
    Open an image and return its pages as upright RGB images.
    Phone photos are turned the right way up using their EXIF orientation.
    """
    frames = []
    with Image.open(image_path) as image:
        multi_page = image.format == "TIFF" and getattr(image, "n_frames", 1) > 1
        frame_count = image.n_frames if multi_page else 1

        for index in range(frame_count):
            image.seek(index)
            frame = ImageOps.exif_transpose(image.copy())
            frame.info["dpi"] = image.info.get("dpi")
            frames.append(_to_rgb(frame))
    return frames


def page_count(image_path):
    with Image.open(image_path) as image:
        if image.format == "TIFF":
            return getattr(image, "n_frames", 1)
    return 1


def thumbnail(image_path, size=280):
    """Small upright preview of the first page of an image."""
    with Image.open(image_path) as image:
        image.draft("RGB", (size * 2, size * 2))  # fast loading for big JPEGs
        preview = ImageOps.exif_transpose(image.copy())
    preview = _to_rgb(preview)
    preview.thumbnail((size, size))
    return preview


def _to_rgb(image):
    """Convert to RGB; transparent parts become white instead of black."""
    if image.mode in ("RGBA", "LA", "P", "PA"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _resolution(image):
    """
    DPI for the PDF page. Uses the DPI stored in the image (e.g. scans), but
    never makes a page larger than A4, so big photos don't become huge pages.
    """
    dpi = image.info.get("dpi")
    dpi = float(dpi[0]) if dpi and dpi[0] else 72.0
    dpi = max(dpi, 72.0)
    return max(dpi, max(image.size) / A4_LONG_SIDE_INCH)


def _image_to_pdf_bytes(image_path, angle=0):
    """Convert one image file (all its pages) to PDF bytes, rotated clockwise by angle."""
    writer = PdfWriter()
    for frame in load_frames(image_path):
        if angle % 360:
            dpi = frame.info.get("dpi")
            frame = frame.rotate(-angle, expand=True)  # PIL rotates counter-clockwise
            frame.info["dpi"] = dpi

        buffer = io.BytesIO()
        frame.save(buffer, "PDF", resolution=_resolution(frame), quality=JPEG_QUALITY)
        buffer.seek(0)
        writer.append(buffer)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def imagetopdf(image_paths, output_file, rotations=None):
    """
    Combine images into one PDF, in the given order.
    rotations: optional list with a clockwise angle (0/90/180/270) per image.
    """
    rotations = rotations or [0] * len(image_paths)
    writer = PdfWriter()

    for image_path, angle in zip(image_paths, rotations):
        writer.append(io.BytesIO(_image_to_pdf_bytes(image_path, angle)))

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file


def imagestopdfs(image_paths, output_folder, rotations=None):
    """
    Save every image as its own PDF in output_folder (photo.jpg -> photo.pdf).
    Existing files are not overwritten: a number is added instead.
    Returns the list of created files.
    """
    rotations = rotations or [0] * len(image_paths)
    output_folder = Path(output_folder)
    created = []

    for image_path, angle in zip(image_paths, rotations):
        output_file = _unique_path(output_folder / f"{Path(image_path).stem}.pdf", created)
        output_file.write_bytes(_image_to_pdf_bytes(image_path, angle))
        created.append(output_file)

    return created


def _unique_path(path, taken):
    candidate, number = path, 1
    while candidate.exists() or candidate in taken:
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        number += 1
    return candidate


def folder_to_pdf(folder_path, output_filename="merged.pdf"):
    folder = Path(folder_path)

    image_paths = sorted(
        (
            file
            for file in folder.iterdir()
            if file.is_file()
            and file.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda f: [
            int(x) if x.isdigit() else x.lower()
            for x in re.split(r"(\d+)", f.name)
        ]
    )

    if not image_paths:
        raise ValueError(f"No image files found in {folder}")

    output_file = folder / output_filename

    return imagetopdf(image_paths, output_file)
