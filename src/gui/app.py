from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from PIL import Image
from pypdf import PdfReader

from src.modify.mergepdf import mergepdf
from src.modify.splitpdf import splitpdf
from src.modify.extractpages import extractpages
from src.modify.rotatepdf import rotatepdf
from src.convert.imagetopdf import imagetopdf, imagestopdfs, thumbnail, page_count, IMAGE_EXTENSIONS
from src.utils.page_ranges import parse_page_ranges
from src.utils.thumbnails import page_thumbnails, has_real_previews, PREVIEW_BG


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")


# ==========================================================
# STYLE
# ==========================================================

BG = "#E5F0FF"           # window background (light blue)
CARD = "#FFFFFF"         # cards / panels
SUBCARD = "#F2F6FC"      # panels inside a card
BORDER = "#D6E2F3"
GREEN = "#00843D"        # Technische Unie green
GREEN_HOVER = "#006B31"
GREEN_LIGHT = "#E3F2E9"
NAVY = "#2B2E83"         # Sonepar blue
TEXT = "#1F2937"
MUTED = "#6B7280"

HEADING_FONT = "Bahnschrift SemiBold"
LIGHT_FONT = "Bahnschrift Light"
BODY_FONT = "Segoe UI Variable Text"

MODES = ["Merge PDF", "Extract / Split", "Rotate", "Image to PDF"]

TILE_WIDTH = 160
TILE_PAD = 7
PREVIEW_BOX = 132        # max size of a page preview in a rotate tile


def font(size, weight="normal", family=BODY_FONT):
    return ctk.CTkFont(family=family, size=size, weight=weight)


def heading(size):
    return ctk.CTkFont(family=HEADING_FONT, size=size)


def primary_button(parent, text, command, height=44, **kwargs):
    return ctk.CTkButton(
        parent, text=text, command=command, height=height, corner_radius=10,
        fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white",
        font=heading(15), **kwargs
    )


def secondary_button(parent, text, command, height=36, **kwargs):
    return ctk.CTkButton(
        parent, text=text, command=command, height=height, corner_radius=10,
        fg_color=CARD, hover_color=GREEN_LIGHT, text_color=GREEN,
        border_width=2, border_color=GREEN, font=font(13, "bold"), **kwargs
    )


def small_button(parent, text, command, width=34, **kwargs):
    return ctk.CTkButton(
        parent, text=text, command=command, width=width, height=30, corner_radius=8,
        fg_color=SUBCARD, hover_color=GREEN_LIGHT, text_color=TEXT,
        font=font(15), **kwargs
    )


def arrow_button(parent, text, command):
    """Small square button with a rotate arrow (↺ / ↻)."""
    button = small_button(parent, text, command)
    button.configure(font=ctk.CTkFont(family="Segoe UI Symbol", size=17), text_color=GREEN)
    return button


def card(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER, **kwargs)


class PDFToolApp:

    def __init__(self):
        self.root = ctk.CTk(fg_color=BG)

        icon_path = Path("images/logoTU_icon.ico")
        self.root.iconbitmap(icon_path)
        self.root.title("Transform PDF")
        self.root.geometry("1200x740")
        self.root.minsize(1160, 660)

        # Merge
        self.merge_pdf_paths = []
        # Extract / split
        self.split_pdf_path = None
        self.split_pdf_page_count = None
        # Rotate
        self.rotate_pdf_path = None
        self.rotate_angles = []          # clockwise rotation per page (0, 90, 180, 270)
        self.rotate_thumbs = []          # PIL images per page
        self.rotate_tiles = []           # widgets per page
        self.rotate_columns = 0
        # Image to PDF
        self.image_items = []            # dicts: path, thumb, angle, pages + widgets
        self.image_columns = 0

        self.mode_frames = {}

        self.create_widgets()
        self.show_mode(MODES[0])

    # ==========================================================
    # LAYOUT
    # ==========================================================

    def create_widgets(self):
        self.build_header()

        self.content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=28, pady=(20, 10))

        builders = {
            "Merge PDF": self.build_merge_frame,
            "Extract / Split": self.build_split_frame,
            "Rotate": self.build_rotate_frame,
            "Image to PDF": self.build_image_frame,
        }
        for mode, builder in builders.items():
            frame = card(self.content_frame)
            builder(frame)
            self.mode_frames[mode] = frame

        self.status_label = ctk.CTkLabel(self.root, text="", font=font(12), text_color=MUTED, anchor="w")
        self.status_label.pack(fill="x", padx=32, pady=(0, 10))

    def build_header(self):
        header = ctk.CTkFrame(self.root, fg_color=CARD, corner_radius=0, height=96)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Green accent line under the header
        ctk.CTkFrame(self.root, fg_color=GREEN, corner_radius=0, height=4).pack(fill="x")

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28)

        # Technische Unie logo (prominent, left)
        logo = Image.open(Path("images/logoTU.png"))
        logo_height = 54
        logo_width = int(logo.width * logo_height / logo.height)
        self.logo_image = ctk.CTkImage(light_image=logo, size=(logo_width, logo_height))
        ctk.CTkLabel(inner, text="", image=self.logo_image).pack(side="left")

        # Divider
        ctk.CTkFrame(inner, fg_color=BORDER, width=2, height=56, corner_radius=1).pack(side="left", padx=24)

        # App name + author
        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.pack(side="left")
        title_row = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(title_row, text="Transform", font=heading(30), text_color=NAVY).pack(side="left")
        ctk.CTkLabel(title_row, text=" PDF", font=heading(30), text_color=GREEN).pack(side="left")
        ctk.CTkLabel(title_frame, text="by Jesse Metz", font=ctk.CTkFont(family=LIGHT_FONT, size=14),
                     text_color=MUTED, height=16).pack(anchor="w", padx=(2, 0))

        # Mode switch (top right)
        self.mode_switch = ctk.CTkSegmentedButton(
            inner, values=MODES, command=self.show_mode,
            font=heading(14), height=42, corner_radius=12, border_width=4,
            fg_color=SUBCARD, unselected_color=SUBCARD, unselected_hover_color=GREEN_LIGHT,
            selected_color=GREEN, selected_hover_color=GREEN_HOVER,
            text_color=TEXT, dynamic_resizing=False, width=520,
        )
        self.mode_switch.pack(side="right")
        self._style_mode_buttons()

    def _style_mode_buttons(self):
        # Segmented buttons share one text colour; give unselected ones dark text.
        selected = self.mode_switch.get()
        for value, button in self.mode_switch._buttons_dict.items():
            button.configure(text_color="white" if value == selected else TEXT)

    def show_mode(self, mode):
        for frame in self.mode_frames.values():
            frame.pack_forget()
        self.mode_frames[mode].pack(fill="both", expand=True)
        self.mode_switch.set(mode)
        self._style_mode_buttons()
        self.set_status("")

    def set_status(self, text):
        self.status_label.configure(text=text)

    def section_title(self, frame, title, subtitle):
        ctk.CTkLabel(frame, text=title, font=heading(22), text_color=NAVY).pack(anchor="w", padx=28, pady=(24, 0))
        ctk.CTkLabel(frame, text=subtitle, font=font(13), text_color=MUTED).pack(anchor="w", padx=28, pady=(0, 16))

    # ==========================================================
    # MERGE
    # ==========================================================

    def build_merge_frame(self, frame):
        self.section_title(frame, "Merge PDF documents",
                           "Combine several PDF files into one. Put them in the right order first.")

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(0, 24))

        # Left: file list
        list_frame = ctk.CTkFrame(body, fg_color=SUBCARD, corner_radius=12)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        self.merge_empty_label = ctk.CTkLabel(list_frame, text="No files selected yet", font=font(12), text_color=MUTED)
        self.merge_empty_label.pack(anchor="w", padx=16, pady=(10, 0))

        inner = tk.Frame(list_frame, bg=SUBCARD)
        inner.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        scrollbar = ctk.CTkScrollbar(inner, button_color="#C3D1E6", button_hover_color="#A9BBD6")
        self.merge_listbox = tk.Listbox(
            inner, font=(BODY_FONT, 11), selectmode=tk.SINGLE, activestyle="none",
            borderwidth=0, highlightthickness=0, relief="flat",
            bg=SUBCARD, fg=TEXT, selectbackground=GREEN, selectforeground="white",
        )
        self.merge_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.merge_listbox.yview)
        self.merge_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Right: actions
        actions = ctk.CTkFrame(body, fg_color="transparent", width=230)
        actions.pack(side="left", fill="y")
        actions.pack_propagate(False)

        secondary_button(actions, "＋  Select PDF files", self.select_merge_files, height=42).pack(fill="x")

        ctk.CTkLabel(actions, text="Order", font=heading(14), text_color=TEXT).pack(anchor="w", pady=(22, 4))
        ctk.CTkLabel(actions, text="Select a file and move it.", font=font(12), text_color=MUTED).pack(anchor="w")
        order_row = ctk.CTkFrame(actions, fg_color="transparent")
        order_row.pack(fill="x", pady=(6, 0))
        order_row.columnconfigure((0, 1), weight=1)
        small_button(order_row, "▲  Up", self.move_up, width=100).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        small_button(order_row, "▼  Down", self.move_down, width=100).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        small_button(actions, "✕  Remove from list", self.remove_merge_file).pack(fill="x", pady=(8, 0))

        primary_button(actions, "Merge PDFs", self.save_merged_pdf, height=48).pack(side="bottom", fill="x")

    def select_merge_files(self):
        pdf_files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if not pdf_files: return

        self.merge_pdf_paths = [Path(pdf) for pdf in pdf_files]
        self.refresh_merge_files()

    def refresh_merge_files(self):
        self.merge_listbox.delete(0, tk.END)
        for index, pdf in enumerate(self.merge_pdf_paths, start=1):
            self.merge_listbox.insert(tk.END, f"  {index}.  {pdf.name}")

        count = len(self.merge_pdf_paths)
        self.merge_empty_label.configure(
            text=f"{count} file{'s' if count != 1 else ''} selected" if count else "No files selected yet"
        )

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

    def remove_merge_file(self):
        selection = self.merge_listbox.curselection()
        if not selection: return

        index = selection[0]
        del self.merge_pdf_paths[index]
        self.refresh_merge_files()
        if self.merge_pdf_paths:
            self.merge_listbox.selection_set(min(index, len(self.merge_pdf_paths) - 1))

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
        self.set_status(f"✔  Merged PDF saved: {output_file}")
        messagebox.showinfo("Success", f"Merged PDF saved:\n{output_file}")

    # ==========================================================
    # SPLIT / EXTRACT
    # ==========================================================

    def build_split_frame(self, frame):
        self.section_title(frame, "Extract / split PDF pages",
                           "Save every page as a separate file, or keep only the pages you need.")

        # File selection row
        file_row = ctk.CTkFrame(frame, fg_color=SUBCARD, corner_radius=12)
        file_row.pack(fill="x", padx=28)
        secondary_button(file_row, "＋  Select PDF", self.select_split_file, width=180).pack(side="left", padx=14, pady=14)
        file_text = ctk.CTkFrame(file_row, fg_color="transparent")
        file_text.pack(side="left", fill="x", expand=True)
        self.file_label = ctk.CTkLabel(file_text, text="No PDF selected", font=font(13, "bold"), text_color=TEXT, anchor="w")
        self.file_label.pack(anchor="w")
        self.page_count_label = ctk.CTkLabel(file_text, text="", font=font(12), text_color=MUTED, anchor="w", height=16)
        self.page_count_label.pack(anchor="w")

        # Two options side by side
        options = ctk.CTkFrame(frame, fg_color="transparent")
        options.pack(fill="both", expand=True, padx=28, pady=(20, 24))
        options.columnconfigure((0, 1), weight=1, uniform="options")
        options.rowconfigure(0, weight=1)

        split_box = ctk.CTkFrame(options, fg_color="transparent", border_width=1, border_color=BORDER, corner_radius=12)
        split_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(split_box, text="Split into single pages", font=heading(17), text_color=TEXT).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(split_box, text="Every page becomes its own PDF file,\nsaved in a folder you choose.",
                     font=font(12), text_color=MUTED, justify="left").pack(anchor="w", padx=20)
        primary_button(split_box, "Split Into Individual Pages", self.save_split_pdf).pack(side="bottom", fill="x", padx=20, pady=20)

        extract_box = ctk.CTkFrame(options, fg_color="transparent", border_width=1, border_color=BORDER, corner_radius=12)
        extract_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        ctk.CTkLabel(extract_box, text="Extract specific pages", font=heading(17), text_color=TEXT).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(extract_box, text="Save only the pages you need in one new PDF.",
                     font=font(12), text_color=MUTED, justify="left").pack(anchor="w", padx=20)
        ctk.CTkLabel(extract_box, text="Pages", font=font(13, "bold"), text_color=TEXT).pack(anchor="w", padx=20, pady=(16, 2))
        self.page_range_entry = ctk.CTkEntry(extract_box, height=38, corner_radius=10, font=font(13),
                                             border_color=BORDER, placeholder_text="e.g. 4-9 or 1,3,5-8")
        self.page_range_entry.pack(fill="x", padx=20)
        ctk.CTkLabel(extract_box, text="Examples: 4-9 or 1,3,5-8", font=font(12), text_color=MUTED).pack(anchor="w", padx=20, pady=(4, 0))
        primary_button(extract_box, "Save Selected Pages", self.save_selected_pages).pack(side="bottom", fill="x", padx=20, pady=20)

    def select_split_file(self):
        pdf_file = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not pdf_file: return

        self.split_pdf_path = Path(pdf_file)
        reader = PdfReader(pdf_file)
        self.split_pdf_page_count = len(reader.pages)
        self.file_label.configure(text=self.split_pdf_path.name)
        self.page_count_label.configure(text=f"{self.split_pdf_page_count} pages (range: 1-{self.split_pdf_page_count})")

    def save_selected_pages(self):
        if self.split_pdf_path is None:
            messagebox.showwarning("Extract pages", "Select a PDF first.")
            return

        page_text = self.page_range_entry.get().replace(" ", "")
        try:
            pages = parse_page_ranges(page_text, self.split_pdf_page_count)
        except ValueError as error:
            messagebox.showwarning("Extract pages", str(error))
            return

        default_filename = f"{self.split_pdf_path.stem}-pages-{page_text}.pdf"

        output_file = filedialog.asksaveasfilename(
            title="Save PDF",
            initialdir=self.split_pdf_path.parent,
            initialfile=default_filename,
            defaultextension=".pdf"
        )
        if not output_file: return

        extractpages(pdf_path=self.split_pdf_path, output_file=output_file, pages=pages)
        self.set_status(f"✔  Saved: {output_file}")
        messagebox.showinfo("Success", f"Saved:\n{output_file}")

    def save_split_pdf(self):
        if self.split_pdf_path is None:
            messagebox.showwarning("Split PDF", "Select a PDF first.")
            return

        output_folder = filedialog.askdirectory(title="Output Folder")
        if not output_folder: return

        splitpdf(pdf_path=self.split_pdf_path, output_folder=output_folder)
        self.set_status(f"✔  Files saved to: {output_folder}")
        messagebox.showinfo("Success", f"Files saved to:\n{output_folder}")

    # ==========================================================
    # ROTATE
    # ==========================================================

    def build_rotate_frame(self, frame):
        self.section_title(frame, "Rotate pages",
                           "Use the arrows under a page to rotate it, or click the page to turn it a quarter clockwise.")

        # Toolbar: file + "all pages" actions
        toolbar = ctk.CTkFrame(frame, fg_color=SUBCARD, corner_radius=12)
        toolbar.pack(fill="x", padx=28)
        secondary_button(toolbar, "＋  Select PDF", self.select_rotate_file, width=180).pack(side="left", padx=14, pady=14)

        file_text = ctk.CTkFrame(toolbar, fg_color="transparent")
        file_text.pack(side="left", fill="x", expand=True)
        self.rotate_file_label = ctk.CTkLabel(file_text, text="No PDF selected", font=font(13, "bold"), text_color=TEXT, anchor="w")
        self.rotate_file_label.pack(anchor="w")
        self.rotate_info_label = ctk.CTkLabel(file_text, text="", font=font(12), text_color=MUTED, anchor="w", height=16)
        self.rotate_info_label.pack(anchor="w")

        all_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        all_frame.pack(side="right", padx=14)
        ctk.CTkLabel(all_frame, text="All pages", font=font(12), text_color=MUTED).pack(side="left", padx=(0, 8))
        arrow_button(all_frame, "↺", lambda: self.rotate_all(-90)).pack(side="left", padx=2)
        arrow_button(all_frame, "↻", lambda: self.rotate_all(90)).pack(side="left", padx=2)
        small_button(all_frame, "Reset", self.reset_rotation, width=60).pack(side="left", padx=(8, 0))

        # Bottom bar with save button
        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=28, pady=(10, 24))
        self.rotate_summary_label = ctk.CTkLabel(bottom, text="", font=font(13), text_color=MUTED)
        self.rotate_summary_label.pack(side="left")
        primary_button(bottom, "Save Rotated PDF", self.save_rotated_pdf, width=240, height=48).pack(side="right")

        # Page grid
        self.rotate_grid = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#C3D1E6", scrollbar_button_hover_color="#A9BBD6",
        )
        self.rotate_grid.pack(fill="both", expand=True, padx=20, pady=(12, 0))
        self.rotate_grid._parent_canvas.bind("<Configure>", lambda event: self.layout_rotate_tiles(), add="+")

        self.rotate_placeholder = ctk.CTkLabel(
            self.rotate_grid, text="Select a PDF to see its pages here.",
            font=font(14), text_color=MUTED,
        )
        self.rotate_placeholder.grid(row=0, column=0, padx=10, pady=60, sticky="w")

    def select_rotate_file(self):
        pdf_file = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if not pdf_file: return

        self.rotate_file_label.configure(text="Loading pages…")
        self.root.update_idletasks()
        self.root.configure(cursor="watch")
        try:
            thumbs = page_thumbnails(pdf_file)
        except Exception as error:
            messagebox.showerror("Rotate pages", f"Could not open this PDF:\n{error}")
            self.rotate_file_label.configure(text="No PDF selected" if self.rotate_pdf_path is None else self.rotate_pdf_path.name)
            return
        finally:
            self.root.configure(cursor="")

        self.rotate_pdf_path = Path(pdf_file)
        self.rotate_thumbs = thumbs
        self.rotate_angles = [0] * len(thumbs)

        count = len(thumbs)
        self.rotate_file_label.configure(text=self.rotate_pdf_path.name)
        info = f"{count} page{'s' if count != 1 else ''}"
        if not has_real_previews():
            info += "  ·  simplified previews (install 'pymupdf' to see page content)"
        self.rotate_info_label.configure(text=info)

        self.build_rotate_tiles()

    def build_rotate_tiles(self):
        for tile in self.rotate_tiles:
            tile["frame"].destroy()
        self.rotate_tiles = []
        self.rotate_placeholder.grid_forget()

        for index in range(len(self.rotate_thumbs)):
            self.rotate_tiles.append(self.create_rotate_tile(index))
            self.update_rotate_tile(index)

        self.rotate_columns = 0  # force a new layout
        self.layout_rotate_tiles()
        self.update_rotate_summary()
        self.rotate_grid._parent_canvas.yview_moveto(0)

    def create_rotate_tile(self, index):
        tile = ctk.CTkFrame(self.rotate_grid, fg_color=CARD, corner_radius=12, border_width=2,
                            border_color=BORDER, width=TILE_WIDTH)

        preview_area = ctk.CTkFrame(tile, fg_color=PREVIEW_BG, corner_radius=10,
                                    width=TILE_WIDTH - 16, height=PREVIEW_BOX + 12)
        preview_area.pack(padx=8, pady=(8, 4))
        preview_area.pack_propagate(False)
        image_label = ctk.CTkLabel(preview_area, text="", cursor="hand2")
        image_label.pack(expand=True)
        image_label.bind("<Button-1>", lambda event, i=index: self.rotate_page(i, 90))

        controls = ctk.CTkFrame(tile, fg_color="transparent")
        controls.pack(fill="x", padx=8, pady=(0, 8))
        arrow_button(controls, "↺", lambda i=index: self.rotate_page(i, -90)).pack(side="left")
        arrow_button(controls, "↻", lambda i=index: self.rotate_page(i, 90)).pack(side="right")

        labels = ctk.CTkFrame(controls, fg_color="transparent")
        labels.pack(expand=True)
        ctk.CTkLabel(labels, text=f"Page {index + 1}", font=font(12, "bold"), text_color=TEXT, height=16).pack()
        angle_label = ctk.CTkLabel(labels, text="", font=font(11), text_color=MUTED, height=14)
        angle_label.pack()

        return {"frame": tile, "image_label": image_label, "angle_label": angle_label}

    def layout_rotate_tiles(self):
        if not self.rotate_tiles: return

        width = self.rotate_grid._parent_canvas.winfo_width()
        columns = max(1, width // (TILE_WIDTH + 2 * TILE_PAD))
        if columns == self.rotate_columns: return
        self.rotate_columns = columns

        for index, tile in enumerate(self.rotate_tiles):
            tile["frame"].grid(row=index // columns, column=index % columns, padx=TILE_PAD, pady=TILE_PAD)

    def rotate_page(self, index, delta):
        self.rotate_angles[index] = (self.rotate_angles[index] + delta) % 360
        self.update_rotate_tile(index)
        self.update_rotate_summary()

    def rotate_all(self, delta):
        for index in range(len(self.rotate_angles)):
            self.rotate_page(index, delta)

    def reset_rotation(self):
        for index in range(len(self.rotate_angles)):
            self.rotate_angles[index] = 0
            self.update_rotate_tile(index)
        self.update_rotate_summary()

    def update_rotate_tile(self, index):
        angle = self.rotate_angles[index]
        tile = self.rotate_tiles[index]

        image = self.rotate_thumbs[index].rotate(-angle, expand=True)  # PIL rotates counter-clockwise
        scale = PREVIEW_BOX / max(image.size)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        tile["ctk_image"] = ctk.CTkImage(light_image=image, size=size)
        tile["image_label"].configure(image=tile["ctk_image"])

        labels = {0: "", 90: "↻ 90° right", 180: "180°", 270: "↺ 90° left"}
        tile["angle_label"].configure(text=labels[angle], text_color=GREEN if angle else MUTED)
        tile["frame"].configure(border_color=GREEN if angle else BORDER)

    def update_rotate_summary(self):
        changed = sum(1 for angle in self.rotate_angles if angle)
        if not self.rotate_angles:
            text = ""
        elif changed == 0:
            text = "No pages rotated yet."
        else:
            text = f"{changed} of {len(self.rotate_angles)} page{'s' if len(self.rotate_angles) != 1 else ''} will be rotated."
        self.rotate_summary_label.configure(text=text, text_color=GREEN if changed else MUTED)

    def save_rotated_pdf(self):
        if self.rotate_pdf_path is None:
            messagebox.showwarning("Rotate pages", "Select a PDF first.")
            return
        if not any(self.rotate_angles):
            messagebox.showwarning("Rotate pages", "No pages have been rotated yet.")
            return

        output_file = filedialog.asksaveasfilename(
            title="Save rotated PDF",
            initialdir=self.rotate_pdf_path.parent,
            initialfile=f"{self.rotate_pdf_path.stem}-rotated.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output_file: return

        page_angles = {index + 1: angle for index, angle in enumerate(self.rotate_angles) if angle}
        rotatepdf(pdf_path=self.rotate_pdf_path, output_file=output_file, page_angles=page_angles)
        self.set_status(f"✔  Rotated PDF saved: {output_file}")
        messagebox.showinfo("Success", f"Rotated PDF saved:\n{output_file}")

    # ==========================================================
    # IMAGE TO PDF
    # ==========================================================

    def build_image_frame(self, frame):
        self.section_title(frame, "Image to PDF",
                           "Turn photos, scans and screenshots into PDF. Rotate and order them first if needed.")

        # Toolbar
        toolbar = ctk.CTkFrame(frame, fg_color=SUBCARD, corner_radius=12)
        toolbar.pack(fill="x", padx=28)
        secondary_button(toolbar, "＋  Add images", self.add_images, width=180).pack(side="left", padx=14, pady=14)

        file_text = ctk.CTkFrame(toolbar, fg_color="transparent")
        file_text.pack(side="left", fill="x", expand=True)
        self.image_count_label = ctk.CTkLabel(file_text, text="No images selected", font=font(13, "bold"), text_color=TEXT, anchor="w")
        self.image_count_label.pack(anchor="w")
        types = ", ".join(ext.lstrip(".").upper() for ext in IMAGE_EXTENSIONS if ext not in (".jpeg", ".jfif", ".tiff"))
        ctk.CTkLabel(file_text, text=f"Supported: {types}", font=font(12), text_color=MUTED, anchor="w", height=16).pack(anchor="w")

        all_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        all_frame.pack(side="right", padx=14)
        ctk.CTkLabel(all_frame, text="All images", font=font(12), text_color=MUTED).pack(side="left", padx=(0, 8))
        arrow_button(all_frame, "↺", lambda: self.rotate_all_images(-90)).pack(side="left", padx=2)
        arrow_button(all_frame, "↻", lambda: self.rotate_all_images(90)).pack(side="left", padx=2)
        small_button(all_frame, "Clear", self.clear_images, width=60).pack(side="left", padx=(8, 0))

        # Bottom bar: output choice + convert button
        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=28, pady=(10, 24))
        self.image_summary_label = ctk.CTkLabel(bottom, text="", font=font(13), text_color=MUTED)
        self.image_summary_label.pack(side="left")

        primary_button(bottom, "Convert to PDF", self.save_images_as_pdf, width=240, height=48).pack(side="right")
        self.image_output_mode = ctk.CTkSegmentedButton(
            bottom, values=["One combined PDF", "Separate PDF per image"],
            command=lambda value: self.update_image_summary(),
            font=font(12, "bold"), height=36, corner_radius=10,
            fg_color=SUBCARD, unselected_color=SUBCARD, unselected_hover_color=GREEN_LIGHT,
            selected_color=NAVY, selected_hover_color=NAVY, text_color=TEXT,
        )
        self.image_output_mode.set("One combined PDF")
        self.image_output_mode.pack(side="right", padx=16)
        self._style_output_buttons()

        # Image grid
        self.image_grid = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#C3D1E6", scrollbar_button_hover_color="#A9BBD6",
        )
        self.image_grid.pack(fill="both", expand=True, padx=20, pady=(12, 0))
        self.image_grid._parent_canvas.bind("<Configure>", lambda event: self.layout_image_tiles(), add="+")

        self.image_placeholder = ctk.CTkLabel(
            self.image_grid, text="Add one or more images to get started.",
            font=font(14), text_color=MUTED,
        )
        self.image_placeholder.grid(row=0, column=0, padx=10, pady=60, sticky="w")

    def _style_output_buttons(self):
        selected = self.image_output_mode.get()
        for value, button in self.image_output_mode._buttons_dict.items():
            button.configure(text_color="white" if value == selected else TEXT)

    def add_images(self):
        patterns = " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS)
        files = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Images", patterns), ("All files", "*.*")],
        )
        if not files: return
        self.add_image_files(files)

    def add_image_files(self, files):
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        failed = []
        try:
            for file in files:
                path = Path(file)
                try:
                    item = {"path": path, "thumb": thumbnail(path), "angle": 0, "pages": page_count(path)}
                except Exception:
                    failed.append(path.name)
                    continue
                self.create_image_tile(item)
                self.image_items.append(item)
        finally:
            self.root.configure(cursor="")

        self.refresh_image_grid()
        if failed:
            messagebox.showwarning("Image to PDF", "These files could not be opened as an image:\n\n" + "\n".join(failed))

    def create_image_tile(self, item):
        tile = ctk.CTkFrame(self.image_grid, fg_color=CARD, corner_radius=12, border_width=2,
                            border_color=BORDER, width=TILE_WIDTH)

        # Top row: order number + remove
        top = ctk.CTkFrame(tile, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 0))
        item["number_label"] = ctk.CTkLabel(top, text="", width=26, height=22, corner_radius=11,
                                            fg_color=NAVY, text_color="white", font=font(11, "bold"))
        item["number_label"].pack(side="left")
        ctk.CTkButton(top, text="✕", width=24, height=22, corner_radius=8, fg_color="transparent",
                      hover_color="#FDE2E2", text_color=MUTED, font=font(12),
                      command=lambda: self.remove_image(item)).pack(side="right")

        preview_area = ctk.CTkFrame(tile, fg_color=PREVIEW_BG, corner_radius=10,
                                    width=TILE_WIDTH - 16, height=PREVIEW_BOX + 12)
        preview_area.pack(padx=8, pady=4)
        preview_area.pack_propagate(False)
        image_label = ctk.CTkLabel(preview_area, text="", cursor="hand2")
        image_label.pack(expand=True)
        image_label.bind("<Button-1>", lambda event: self.rotate_image(item, 90))

        name = item["path"].name
        if len(name) > 20:
            name = name[:12] + "…" + name[-7:]
        ctk.CTkLabel(tile, text=name, font=font(11, "bold"), text_color=TEXT, height=16).pack(padx=8)
        info_label = ctk.CTkLabel(tile, text="", font=font(11), text_color=MUTED, height=14)
        info_label.pack(padx=8)

        controls = ctk.CTkFrame(tile, fg_color="transparent")
        controls.pack(fill="x", padx=8, pady=(4, 8))
        controls.columnconfigure((0, 1, 2, 3), weight=1)
        order_font = ctk.CTkFont(family="Segoe UI Symbol", size=12)
        arrow_button(controls, "↺", lambda: self.rotate_image(item, -90)).grid(row=0, column=0, sticky="w")
        move_left = small_button(controls, "◀", lambda: self.move_image(item, -1))
        move_left.configure(font=order_font)
        move_left.grid(row=0, column=1)
        move_right = small_button(controls, "▶", lambda: self.move_image(item, 1))
        move_right.configure(font=order_font)
        move_right.grid(row=0, column=2)
        arrow_button(controls, "↻", lambda: self.rotate_image(item, 90)).grid(row=0, column=3, sticky="e")

        item.update(frame=tile, image_label=image_label, info_label=info_label)
        self.update_image_tile(item)

    def update_image_tile(self, item):
        angle = item["angle"]
        image = item["thumb"].rotate(-angle, expand=True)
        scale = PREVIEW_BOX / max(image.size)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        item["ctk_image"] = ctk.CTkImage(light_image=image, size=size)
        item["image_label"].configure(image=item["ctk_image"])

        parts = []
        if item["pages"] > 1:
            parts.append(f"{item['pages']} pages")
        if angle:
            parts.append({90: "↻ 90° right", 180: "180°", 270: "↺ 90° left"}[angle])
        item["info_label"].configure(text="  ·  ".join(parts), text_color=GREEN if angle else MUTED)
        item["frame"].configure(border_color=GREEN if angle else BORDER)

    def refresh_image_grid(self):
        """Re-place all tiles in the current order and update numbers and summary."""
        if self.image_items:
            self.image_placeholder.grid_forget()
        else:
            self.image_placeholder.grid(row=0, column=0, padx=10, pady=60, sticky="w")

        for number, item in enumerate(self.image_items, start=1):
            item["number_label"].configure(text=str(number))
        self.image_columns = 0
        self.layout_image_tiles()

        count = len(self.image_items)
        self.image_count_label.configure(
            text=f"{count} image{'s' if count != 1 else ''} selected" if count else "No images selected"
        )
        self.update_image_summary()

    def layout_image_tiles(self):
        if not self.image_items: return

        width = self.image_grid._parent_canvas.winfo_width()
        columns = max(1, width // (TILE_WIDTH + 2 * TILE_PAD))
        if columns == self.image_columns: return
        self.image_columns = columns

        for index, item in enumerate(self.image_items):
            item["frame"].grid(row=index // columns, column=index % columns, padx=TILE_PAD, pady=TILE_PAD)

    def rotate_image(self, item, delta):
        item["angle"] = (item["angle"] + delta) % 360
        self.update_image_tile(item)
        self.update_image_summary()

    def rotate_all_images(self, delta):
        for item in self.image_items:
            self.rotate_image(item, delta)

    def move_image(self, item, step):
        index = self.image_items.index(item)
        new_index = index + step
        if not 0 <= new_index < len(self.image_items): return

        self.image_items[index], self.image_items[new_index] = self.image_items[new_index], self.image_items[index]
        self.refresh_image_grid()

    def remove_image(self, item):
        self.image_items.remove(item)
        item["frame"].destroy()
        self.refresh_image_grid()

    def clear_images(self):
        for item in self.image_items:
            item["frame"].destroy()
        self.image_items = []
        self.refresh_image_grid()

    def update_image_summary(self):
        self._style_output_buttons()
        count = len(self.image_items)
        if not count:
            self.image_summary_label.configure(text="")
            return

        if self.image_output_mode.get() == "One combined PDF":
            pages = sum(item["pages"] for item in self.image_items)
            text = f"1 PDF with {pages} page{'s' if pages != 1 else ''}, in the order shown."
        else:
            text = f"{count} separate PDF{'s' if count != 1 else ''}, one per image."
        self.image_summary_label.configure(text=text)

    def save_images_as_pdf(self):
        if not self.image_items:
            messagebox.showwarning("Image to PDF", "Add at least one image first.")
            return

        paths = [item["path"] for item in self.image_items]
        rotations = [item["angle"] for item in self.image_items]
        first = paths[0]

        if self.image_output_mode.get() == "One combined PDF":
            output_file = filedialog.asksaveasfilename(
                title="Save PDF",
                initialdir=first.parent,
                initialfile=f"{first.stem}.pdf",
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            if not output_file: return
            if self._run_busy(lambda: imagetopdf(paths, output_file, rotations)) is None: return
            self.set_status(f"✔  PDF saved: {output_file}")
            messagebox.showinfo("Success", f"PDF saved:\n{output_file}")
        else:
            output_folder = filedialog.askdirectory(title="Folder for the PDF files", initialdir=first.parent)
            if not output_folder: return
            created = self._run_busy(lambda: imagestopdfs(paths, output_folder, rotations))
            if created is None: return
            self.set_status(f"✔  {len(created)} PDF files saved to: {output_folder}")
            messagebox.showinfo("Success", f"{len(created)} PDF files saved to:\n{output_folder}")

    def _run_busy(self, task):
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        try:
            return task()
        except Exception as error:
            messagebox.showerror("Image to PDF", f"Something went wrong:\n{error}")
            return None
        finally:
            self.root.configure(cursor="")

    def run(self):
        self.root.mainloop()
