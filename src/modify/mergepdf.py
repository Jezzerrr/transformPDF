from pypdf import PdfWriter


def mergepdf(pdf_paths, output_file):
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        writer.append(pdf_path)

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file
