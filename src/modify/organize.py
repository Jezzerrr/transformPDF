from pathlib import Path

from pypdf import PdfReader, PdfWriter


def write_pages(pages, output_file, readers=None):
    """
    Write a new PDF from a list of pages.
    pages: list of (source_pdf_path, page_index (0-based), clockwise_angle)
    Pages may come from different PDFs and may appear more than once.
    """
    readers = {} if readers is None else readers
    writer = PdfWriter()

    for source, index, angle in pages:
        source = Path(source)
        if source not in readers:
            readers[source] = PdfReader(source)
        new_page = writer.add_page(readers[source].pages[index])
        if angle % 360:
            new_page.rotation = (new_page.rotation + angle) % 360

    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file


def write_page_groups(groups, output_files):
    """Write several PDFs; groups[i] (a list like for write_pages) goes to output_files[i]."""
    readers = {}
    for pages, output_file in zip(groups, output_files):
        write_pages(pages, output_file, readers)
    return output_files


def unique_path(path, taken=()):
    """path, or 'name (1).pdf', 'name (2).pdf' ... if it already exists."""
    path = Path(path)
    candidate, number = path, 1
    while candidate.exists() or candidate in taken:
        candidate = path.with_name(f"{path.stem} ({number}){path.suffix}")
        number += 1
    return candidate
