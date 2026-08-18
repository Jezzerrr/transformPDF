from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from PIL import Image
from pypdf import PdfReader

from src.modify.mergepdf import mergepdf
from src.modify.splitpdf import splitpdf
from src.modify.extractpages import extractpages
from src.utils.page_ranges import parse_page_ranges


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")


class PDFToolApp:

    def __init__(self):
        self.root = ctk.CTk(fg_color='#E5F0FF')
        # self.root = ctk.CTk()

        icon_path = Path("images/logoTU_icon.ico")
        self.root.iconbitmap(icon_path)
        self.root.title("Transform PDF")
        self.root.geometry("1200x700")

        self.merge_pdf_paths = []
        self.split_pdf_path = None
        self.split_pdf_page_count = None

        self.create_widgets()

    def create_widgets(self):
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(fill="x", pady=(15, 5))
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack()

        logo_path = Path("images/logoTU_icon.png")
        self.logo_image = ctk.CTkImage(light_image=Image.open(logo_path), size=(60, 60))
        ctk.CTkLabel(header_content, text="", image=self.logo_image).pack(side="left", padx=(0, 15))

        header_text_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        header_text_frame.pack(side="left")
        ctk.CTkLabel(header_text_frame, text="Transform PDF", font=("Segoe UI", 28, "bold")).pack(anchor="w")
        ctk.CTkLabel(header_text_frame, text="by Jesse Metz", font=("Segoe UI", 12)).pack(anchor="w")

        content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=15)

        merge_frame = ctk.CTkFrame(content_frame)
        merge_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        split_frame = ctk.CTkFrame(content_frame)
        split_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.build_merge_frame(merge_frame)
        self.build_split_frame(split_frame)

    # ==========================================================
    # MERGE
    # ==========================================================

    def build_merge_frame(self, frame):
        ctk.CTkLabel(frame, text="Merge PDF Documents", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkButton(frame, text="Select PDF Files", command=self.select_merge_files).pack(fill="x", padx=20)
        ctk.CTkLabel(frame, text="Select a file below and move it up or down").pack(anchor="w", padx=20, pady=(15, 5))

        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        scrollbar = tk.Scrollbar(list_frame)
        self.merge_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), selectmode=tk.SINGLE, activestyle="none", borderwidth=0, height=10)
        self.merge_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.merge_listbox.yview)
        self.merge_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20)
        ctk.CTkButton(button_frame, text="▲ Up", width=100, command=self.move_up).pack(side="left")
        ctk.CTkButton(button_frame, text="▼ Down", width=100, command=self.move_down).pack(side="left", padx=10)

        ctk.CTkButton(frame, text="Merge PDFs", height=40, command=self.save_merged_pdf).pack(fill="x", padx=20, pady=(15, 20))

    def select_merge_files(self):
        pdf_files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if not pdf_files: return

        self.merge_pdf_paths = [Path(pdf) for pdf in pdf_files]
        self.refresh_merge_files()

    def refresh_merge_files(self):
        self.merge_listbox.delete(0, tk.END)
        for index, pdf in enumerate(self.merge_pdf_paths, start=1):
            self.merge_listbox.insert(tk.END, f"{index}. {pdf.name}")

    def move_up(self):
        selection = self.merge_listbox.curselection()
        if not selection: return

        index = selection[0]
        if index == 0: return

        self.merge_pdf_paths[index], self.merge_pdf_paths[index - 1] = (self.merge_pdf_paths[index - 1], self.merge_pdf_paths[index])
        self.refresh_merge_files()
        self.merge_listbox.selection_set(index - 1)

    def move_down(self):
        selection = self.merge_listbox.curselection()
        if not selection: return

        index = selection[0]
        if index == len(self.merge_pdf_paths) - 1: return

        self.merge_pdf_paths[index], self.merge_pdf_paths[index + 1] = (self.merge_pdf_paths[index + 1], self.merge_pdf_paths[index])
        self.refresh_merge_files()
        self.merge_listbox.selection_set(index + 1)

    def save_merged_pdf(self):
        if len(self.merge_pdf_paths) < 2:
            messagebox.showwarning("Merge PDFs", "Select at least two PDF files.")
            return

        first_file = self.merge_pdf_paths[0]

        output_file = filedialog.asksaveasfilename(
            title="Save merged PDF",
            initialdir=first_file.parent,
            initialfile=f"{first_file.stem}-merged.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output_file: return

        mergepdf(pdf_paths=self.merge_pdf_paths, output_file=output_file)
        messagebox.showinfo("Success", f"Merged PDF saved:\n{output_file}")

    # ==========================================================
    # SPLIT / EXTRACT
    # ==========================================================

    def build_split_frame(self, frame):
        ctk.CTkLabel(frame, text="Extract PDF Pages", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkButton(frame, text="Select PDF", command=self.select_split_file).pack(fill="x", padx=20)

        self.file_label = ctk.CTkLabel(frame, text="No PDF selected")
        self.file_label.pack(anchor="w", padx=20, pady=(15, 5))
        self.page_count_label = ctk.CTkLabel(frame, text="")
        self.page_count_label.pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkButton(frame, text="Split Into Individual Pages", height=40, command=self.save_split_pdf).pack(fill="x", padx=20)
        ctk.CTkLabel(frame, text="━━━━━━━━━━━━━━━━━━━━").pack(pady=20)
        ctk.CTkLabel(frame, text="Extract specific pages", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20)
        ctk.CTkLabel(frame, text="Pages").pack(anchor="w", padx=20, pady=(15, 0))

        self.page_range_entry = ctk.CTkEntry(frame)
        self.page_range_entry.pack(fill="x", padx=20)

        ctk.CTkLabel(frame, text="Examples: 4-9 or 1,3,5-8").pack(anchor="w", padx=20, pady=(5, 0))
        ctk.CTkButton(frame, text="Save Selected Pages", height=40, command=self.save_selected_pages).pack(fill="x", padx=20, pady=(20, 0))

    def select_split_file(self):
        pdf_file = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not pdf_file: return

        self.split_pdf_path = Path(pdf_file)
        reader = PdfReader(pdf_file)
        self.split_pdf_page_count = len(reader.pages)
        self.file_label.configure(text=f"File: {self.split_pdf_path.name}")
        self.page_count_label.configure(text=f"Pages: {self.split_pdf_page_count} (range: 1-{self.split_pdf_page_count})")

    def save_selected_pages(self):
        if self.split_pdf_path is None: return

        page_text = self.page_range_entry.get().replace(" ", "")
        pages = parse_page_ranges(page_text, self.split_pdf_page_count)

        default_filename = f"{self.split_pdf_path.stem}-pages-{page_text}.pdf"

        output_file = filedialog.asksaveasfilename(
            title="Save PDF",
            initialdir=self.split_pdf_path.parent,
            initialfile=default_filename,
            defaultextension=".pdf"
        )
        if not output_file: return

        extractpages(pdf_path=self.split_pdf_path, output_file=output_file, pages=pages)
        messagebox.showinfo("Success", f"Saved:\n{output_file}")

    def save_split_pdf(self):
        if self.split_pdf_path is None: return

        output_folder = filedialog.askdirectory(title="Output Folder")
        if not output_folder: return

        splitpdf(pdf_path=self.split_pdf_path, output_folder=output_folder)

        messagebox.showinfo("Success", f"Files saved to:\n{output_folder}")

    def run(self):
        self.root.mainloop()
