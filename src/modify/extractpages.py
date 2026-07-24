from pypdf import PdfReader, PdfWriter


def extractpages(pdf_path, output_file, pages):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_number in pages:
        writer.add_page(reader.pages[page_number - 1])

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
