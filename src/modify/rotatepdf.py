from pypdf import PdfReader, PdfWriter


def rotatepdf(pdf_path, output_file, angle=90, page_angles=None):
    """
    Rotate pages of a PDF clockwise.

    - Without page_angles: every page is rotated by `angle` degrees.
    - With page_angles (dict {page_number: angle}, page numbers start at 1):
      only the listed pages are rotated, each by its own angle.

    Angles must be multiples of 90.
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_number, page in enumerate(reader.pages, start=1):
        if page_angles is None:
            page_angle = angle
        else:
            page_angle = page_angles.get(page_number, 0)

        page_angle %= 360
        if page_angle:
            # Keep /Rotate between 0 and 270 (some viewers dislike 360 or more)
            page.rotation = (page.rotation + page_angle) % 360

        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
