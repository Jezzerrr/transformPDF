from pypdf import PdfReader, PdfWriter


def rotatepdf(pdf_path, output_file, angle=90):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
