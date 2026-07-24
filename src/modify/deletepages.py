from pypdf import PdfReader, PdfWriter


def deletepages(pdf_path, output_file, pages):
    pages = set(pages)

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_number, page in enumerate(reader.pages, start=1):
        if page_number not in pages:
            writer.add_page(page)

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
