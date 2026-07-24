from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from pypdf import PdfReader

from src.modify.mergepdf import mergepdf
from src.modify.splitpdf import splitpdf
from src.modify.extractpages import extractpages
from src.utils.page_ranges import parse_page_ranges


class PDFToolApp:

    def __init__(self):
        self.root = tk.Tk()

        self.root.title("transformPDF")
        self.root.geometry("900x600")

        self.merge_pdf_paths = []

        self.split_pdf_path = None
        self.split_pdf_page_count = None

        self.create_widgets()

    def create_widgets(self):

        title = tk.Label(self.root, text="transformPDF", font=("Segoe UI", 18, "bold"))
        title.pack(pady=10)

        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        merge_frame = tk.LabelFrame(paned, text="Merge PDFs", padx=10, pady=10)
        split_frame = tk.LabelFrame(paned, text="Split / Extract", padx=10, pady=10)

        paned.add(merge_frame)
        paned.add(split_frame)

        self.build_merge_frame(merge_frame)
        self.build_split_frame(split_frame)

    # ==========================================================
    # MERGE
    # ==========================================================

    def build_merge_frame(self, frame):
        tk.Button(frame, text="Select PDF files", command=self.select_merge_files).pack(fill="x")
        tk.Label(frame, text="Order shown below = merge order").pack(anchor="w", pady=(10, 5))

        list_frame = tk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        self.merge_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.merge_listbox.yview)

        self.merge_listbox.pack(side="left", fill="both", expand=True)

        scrollbar.pack(side="right", fill="y")

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=10)

        tk.Button(button_frame, text="▲ Up", command=self.move_up).pack(side="left")
        tk.Button(button_frame, text="▼ Down", command=self.move_down).pack(side="left", padx=5)

        tk.Button(frame, text="Merge PDFs", command=self.save_merged_pdf).pack(fill="x")

    def select_merge_files(self):

        pdf_files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )

        if not pdf_files:
            return

        self.merge_pdf_paths = [Path(pdf) for pdf in pdf_files]
        self.refresh_merge_listbox()

    def refresh_merge_listbox(self):

        self.merge_listbox.delete(0, tk.END)

        for pdf in self.merge_pdf_paths:
            self.merge_listbox.insert(
                tk.END,
                pdf.name
            )

    def move_up(self):

        selection = self.merge_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        if index == 0:
            return

        self.merge_pdf_paths[index], self.merge_pdf_paths[index - 1] = (
            self.merge_pdf_paths[index - 1],
            self.merge_pdf_paths[index]
        )

        self.refresh_merge_listbox()

        self.merge_listbox.selection_set(index - 1)

    def move_down(self):

        selection = self.merge_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        if index == len(self.merge_pdf_paths) - 1:
            return

        self.merge_pdf_paths[index], self.merge_pdf_paths[index + 1] = (
            self.merge_pdf_paths[index + 1],
            self.merge_pdf_paths[index]
        )

        self.refresh_merge_listbox()

        self.merge_listbox.selection_set(index + 1)

    def save_merged_pdf(self):

        if len(self.merge_pdf_paths) < 2:
            messagebox.showwarning("Merge PDFs", "Select at least two PDF files.")
            return

        first_file = self.merge_pdf_paths[0]
        default_filename = f"{first_file.stem}-merged.pdf"

        output_file = filedialog.asksaveasfilename(
            title="Save merged PDF",
            initialdir=first_file.parent,
            initialfile=default_filename,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )

        if not output_file:
            return

        mergepdf(pdf_paths=self.merge_pdf_paths, output_file=output_file)
        messagebox.showinfo("Success", f"Merged PDF saved:\n{output_file}")

    # ==========================================================
    # SPLIT / EXTRACT
    # ==========================================================

    def build_split_frame(self, frame):
        tk.Button(frame, text="Select PDF", command=self.select_split_file).pack(fill="x")

        self.file_label = tk.Label(frame, text="No PDF selected")
        self.file_label.pack(anchor="w", pady=(10, 5))

        self.page_count_label = tk.Label(frame, text="")
        self.page_count_label.pack(anchor="w", pady=(0, 10))

        tk.Label(frame, text="Pages").pack(anchor="w")

        self.page_range_entry = tk.Entry(frame)
        self.page_range_entry.pack(fill="x", pady=(0, 5))

        tk.Label(frame, text="Examples: 4-9 or 1,3,5-8").pack(anchor="w")
        tk.Button(frame, text="Save Selected Pages", command=self.save_selected_pages).pack(fill="x", pady=(15, 5))
        tk.Button(frame, text="Split Into Individual Pages", command=self.save_split_pdf).pack(fill="x")

    def select_split_file(self):

        pdf_file = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf")]
        )

        if not pdf_file:
            return

        self.split_pdf_path = Path(pdf_file)

        reader = PdfReader(pdf_file)
        self.split_pdf_page_count = len(reader.pages)
        self.file_label.config(text=f"File: {self.split_pdf_path.name}")
        self.page_count_label.config(text=f"Pages: {self.split_pdf_page_count}")

    def save_selected_pages(self):

        if self.split_pdf_path is None:
            return

        pages = parse_page_ranges(
            self.page_range_entry.get(),
            self.split_pdf_page_count
        )

        output_file = filedialog.asksaveasfilename(
            title="Save PDF",
            initialdir=self.split_pdf_path.parent,
            initialfile=f"{self.split_pdf_path.stem}-pages.pdf",
            defaultextension=".pdf"
        )

        if not output_file:
            return

        extractpages(pdf_path=self.split_pdf_path, output_file=output_file, pages=pages)
        messagebox.showinfo("Success", f"Saved:\n{output_file}")

    def save_split_pdf(self):

        if self.split_pdf_path is None:
            return

        output_folder = filedialog.askdirectory(title="Output Folder")

        if not output_folder:
            return

        splitpdf(pdf_path=self.split_pdf_path, output_folder=output_folder)
        messagebox.showinfo("Success", f"Files saved to:\n{output_folder}")

    def run(self):
        self.root.mainloop()
