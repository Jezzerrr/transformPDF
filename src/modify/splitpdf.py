from pathlib import Path

from pypdf import PdfReader, PdfWriter


def splitpdf(pdf_path, output_folder=None):
    pdf_path = Path(pdf_path)

    if output_folder is None:
        output_folder = pdf_path.with_suffix("")
    output_folder = Path(output_folder)

    output_folder.mkdir(exist_ok=True)

    reader = PdfReader(pdf_path)

    for page_number, page in enumerate(reader.pages, start=1):
        output_file = output_folder / f"{pdf_path.stem}_page_{page_number:03d}.pdf"

        writer = PdfWriter()
        writer.add_page(page)

        with open(output_file, "wb") as f:
            writer.write(f)

    return output_folder
