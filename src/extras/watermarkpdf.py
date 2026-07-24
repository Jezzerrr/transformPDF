from pypdf import PdfReader, PdfWriter


def watermarkpdf(pdf_path, watermark_path, output_file, pages=None):
    reader = PdfReader(pdf_path)
    watermark = PdfReader(watermark_path).pages[0]

    writer = PdfWriter()

    if pages is not None:
        pages = set(pages)

    for page_number, page in enumerate(reader.pages, start=1):
        if pages is None or page_number in pages:
            page.merge_page(watermark)

        writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
