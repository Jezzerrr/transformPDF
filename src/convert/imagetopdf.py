from PIL import Image


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
