from pathlib import Path
from PIL import Image
import re


def imagetopdf(image_paths, output_file):
    images = []

    for image_path in image_paths:
        image = Image.open(image_path)

        if image.mode != "RGB":
            image = image.convert("RGB")

        images.append(image)

    images[0].save(
        output_file,
        save_all=True,
        append_images=images[1:]
    )

    return output_file


def folder_to_pdf(folder_path, output_filename="merged.pdf"):
    folder = Path(folder_path)

    image_extensions = {
        ".jpg", ".jpeg", ".png", ".bmp",
        ".gif", ".tif", ".tiff", ".webp"
    }

    image_paths = sorted(
        (
            file
            for file in folder.iterdir()
            if file.is_file()
            and file.suffix.lower() in image_extensions
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