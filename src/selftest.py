"""
Quick check that a packaged TransformPDF.exe has everything it needs.

    TransformPDF.exe --selftest result.txt

Opens the window briefly, makes a PDF preview, converts a HEIC photo and
checks drag & drop, then writes OK (or the error) to result.txt.
"""
import tempfile
import traceback
from pathlib import Path


def run_selftest(result_file):
    lines = []
    try:
        from PIL import Image
        from pypdf import PdfReader, PdfWriter

        from src.gui.app import PDFToolApp
        from src.convert.imagetopdf import imagetopdf, HEIC_SUPPORT
        from src.utils.thumbnails import page_thumbnails, has_real_previews

        folder = Path(tempfile.mkdtemp())

        pdf = folder / "test.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.write(pdf)
        lines.append(f"real previews (pymupdf): {has_real_previews()}")
        lines.append(f"preview size: {page_thumbnails(pdf)[0].size}")

        lines.append(f"heic support: {HEIC_SUPPORT}")
        heic = folder / "photo.heic"
        Image.new("RGB", (400, 300), "orange").save(heic)
        imagetopdf([heic], folder / "photo.pdf", [90])
        lines.append(f"heic -> pdf pages: {len(PdfReader(folder / 'photo.pdf').pages)}")

        app = PDFToolApp()
        app.root.update()
        lines.append(f"drag & drop: {app.root.dnd_available}")
        app.add_pdf_files([pdf])
        lines.append(f"tiles: {len(app.pdf_grid.items)}")
        app.root.destroy()

        lines.append("OK")
    except Exception:
        lines.append("FAILED")
        lines.append(traceback.format_exc())

    Path(result_file).write_text("\n".join(lines), encoding="utf-8")
