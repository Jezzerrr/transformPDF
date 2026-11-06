import re
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from src.convert.imagetopdf import imagetopdf, imagestopdfs, thumbnail, page_count, IMAGE_EXTENSIONS
from src.modify.mergepdf import mergepdf
from src.modify.organize import write_pages, write_page_groups, unique_path
from src.utils.page_ranges import parse_page_groups, format_page_ranges
from src.utils.thumbnails import page_thumbnails, first_page_thumbnail, pdf_page_count, has_real_previews
from src.gui.widgets import (
    BG, CARD, SUBCARD, BORDER, GREEN, NAVY, TEXT, MUTED, RED, GREEN_LIGHT, GREEN_HOVER,
    HEADING_FONT, LIGHT_FONT, SYMBOL_FONT,
    font, heading, primary_button, secondary_button, small_button, symbol_button, card, plural,
    SlideToggle, TileGrid,
)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    TkinterDnD = None


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

MODES = ["Merge PDF", "Edit Pages", "Image to PDF"]

ONE_PDF = "One PDF"
EVERY_PAGE = "Every page separately"
CUSTOM_SPLIT = "Custom split"
IMAGES_COMBINED = "One combined PDF"
IMAGES_SEPARATE = "Separate PDF per image"


if TkinterDnD is not None:
    class AppWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter window that also accepts files dragged in from Explorer."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_available = True
            except Exception:
                self.dnd_available = False
else:
    class AppWindow(ctk.CTk):
        dnd_available = False


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(path).name)]


def is_pdf(path):
    return Path(path).suffix.lower() == ".pdf"


def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


class PDFToolApp:

    def __init__(self):
        self.root = AppWindow(fg_color=BG)

        self.root.iconbitmap(Path("images/logoTU_icon.ico"))
        self.root.title("Transform PDF")
        self.root.geometry("1200x760")
        self.root.minsize(1060, 660)

        self.mode_frames = {}
        self.pages_original = []     # (source, index, thumb) as loaded, for Reset

        self.create_widgets()
        self.show_mode(MODES[0])
        self.setup_file_drop()

    # ==========================================================
    # LAYOUT
    # ==========================================================

    def create_widgets(self):
        self.build_header()

        self.content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=28, pady=(20, 6))

        builders = {
            "Merge PDF": self.build_merge_frame,
            "Edit Pages": self.build_pages_frame,
            "Image to PDF": self.build_image_frame,
        }
        for mode, builder in builders.items():
            frame = card(self.content_frame)
            builder(frame)
            self.mode_frames[mode] = frame

        self.status_label = ctk.CTkLabel(self.root, text="", font=font(12), text_color=MUTED, anchor="w")
        self.status_label.pack(fill="x", padx=32, pady=(0, 8))

    def build_header(self):
        header = ctk.CTkFrame(self.root, fg_color=CARD, corner_radius=0, height=96)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkFrame(self.root, fg_color=GREEN, corner_radius=0, height=4).pack(fill="x")

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28)

        logo = Image.open(Path("images/logoTU.png"))
        logo_height = 58
        logo_width = int(logo.width * logo_height / logo.height)
        self.logo_image = ctk.CTkImage(light_image=logo, size=(logo_width, logo_height))
        ctk.CTkLabel(inner, text="", image=self.logo_image).pack(side="left")

        ctk.CTkFrame(inner, fg_color=BORDER, width=2, height=56, corner_radius=1).pack(side="left", padx=24)

        title_frame = ctk.CTkFrame(inner, fg_color="transparent")
        title_frame.pack(side="left")
        title_row = ctk.CTkFrame(title_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(title_row, text="Transform", font=heading(30), text_color=NAVY).pack(side="left")
        ctk.CTkLabel(title_row, text=" PDF", font=heading(30), text_color=GREEN).pack(side="left")
        ctk.CTkLabel(title_frame, text="by Jesse Metz", font=ctk.CTkFont(family=LIGHT_FONT, size=14),
                     text_color=MUTED, height=16).pack(anchor="w", padx=(2, 0))

        self.mode_switch = ctk.CTkSegmentedButton(
            inner, values=MODES, command=self.show_mode,
            font=heading(15), height=42, corner_radius=12, border_width=4,
            fg_color=SUBCARD, unselected_color=SUBCARD, unselected_hover_color=GREEN_LIGHT,
            selected_color=GREEN, selected_hover_color=GREEN_HOVER,
            text_color=TEXT, dynamic_resizing=False, width=440,
        )
        self.mode_switch.pack(side="right")

    def _style_mode_buttons(self):
        selected = self.mode_switch.get()
        for value, button in self.mode_switch._buttons_dict.items():
            button.configure(text_color="white" if value == selected else TEXT)

    def current_mode(self):
        return self.mode_switch.get()

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
        ctk.CTkLabel(frame, text=title, font=heading(22), text_color=NAVY).pack(anchor="w", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame, text=subtitle, font=font(13), text_color=MUTED).pack(anchor="w", padx=28, pady=(0, 14))

    def toolbar(self, frame, button_text, command):
        """Light bar with an add-button, two lines of text and room for tools on the right."""
        bar = ctk.CTkFrame(frame, fg_color=SUBCARD, corner_radius=12)
        bar.pack(fill="x", padx=28)
        secondary_button(bar, button_text, command, width=190).pack(side="left", padx=14, pady=14)
        text = ctk.CTkFrame(bar, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        title = ctk.CTkLabel(text, text="", font=font(13, "bold"), text_color=TEXT, anchor="w")
        title.pack(anchor="w")
        info = ctk.CTkLabel(text, text="", font=font(12), text_color=MUTED, anchor="w", height=16)
        info.pack(anchor="w")
        tools = ctk.CTkFrame(bar, fg_color="transparent")
        tools.pack(side="right", padx=14)
        return title, info, tools

    def bottom_bar(self, frame):
        bar = ctk.CTkFrame(frame, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=28, pady=(8, 22))
        summary = ctk.CTkLabel(bar, text="", font=font(13), text_color=MUTED, anchor="w", justify="left")
        summary.pack(side="left")
        return bar, summary

    def run_busy(self, title, task):
        """Run task with a busy cursor; show a message instead of crashing on errors."""
        self.root.configure(cursor="watch")
        self.root.update_idletasks()
        try:
            return task()
        except Exception as error:
            messagebox.showerror(title, f"Something went wrong:\n{error}")
            return None
        finally:
            self.root.configure(cursor="")

    # ==========================================================
    # MERGE PDF
    # ==========================================================

    def build_merge_frame(self, frame):
        self.section_title(frame, "Merge PDF documents",
                           "Combine several PDF files into one. Drag the files into the right order first.")
        self.merge_title, self.merge_info, tools = self.toolbar(frame, "＋  Add PDF files", self.select_merge_files)
        self.merge_title.configure(text="No files selected")
        self.merge_info.configure(text="Tip: you can also drag PDF files into this window")
        small_button(tools, "Clear", lambda: self.merge_grid.clear(), width=60).pack(side="left")

        bar, self.merge_summary = self.bottom_bar(frame)
        primary_button(bar, "Merge PDFs", self.save_merged_pdf, width=240, height=48).pack(side="right")

        self.merge_grid = TileGrid(
            frame, "Add two or more PDF files to merge them.\nYou can also drag them from Explorer into this window.",
            on_change=self.update_merge_summary, rotatable=False, stacked=True,
        )
        self.merge_grid.pack(fill="both", expand=True, padx=20, pady=(10, 0))

    def select_merge_files(self):
        files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if files:
            self.add_merge_files(files)

    def add_merge_files(self, files):
        failed = []

        def load():
            for file in files:
                path = Path(file)
                try:
                    item = {"path": path, "title": path.name,
                            "thumb": first_page_thumbnail(path), "pages": pdf_page_count(path)}
                except Exception:
                    failed.append(path.name)
                    continue
                self.merge_grid.add(item)

        self.run_busy("Merge PDF", load)
        self.merge_grid.refresh()
        if failed:
            messagebox.showwarning("Merge PDF", "These files could not be opened as PDF:\n\n" + "\n".join(failed))

    def update_merge_summary(self):
        items = self.merge_grid.items
        pages = sum(item["pages"] for item in items)
        self.merge_title.configure(text=f"{plural(len(items), 'file')} selected" if items else "No files selected")
        self.merge_summary.configure(
            text=f"1 PDF with {plural(pages, 'page')}, files in the order shown." if len(items) > 1
            else ("Add at least one more file." if items else "")
        )

    def save_merged_pdf(self):
        paths = [item["path"] for item in self.merge_grid.items]
        if len(paths) < 2:
            messagebox.showwarning("Merge PDFs", "Select at least two PDF files.")
            return

        output_file = filedialog.asksaveasfilename(
            title="Save merged PDF",
            initialdir=paths[0].parent,
            initialfile=f"{paths[0].stem}-merged.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not output_file: return

        if self.run_busy("Merge PDFs", lambda: mergepdf(pdf_paths=paths, output_file=output_file)) is None: return
        self.set_status(f"✔  Merged PDF saved: {output_file}")
        messagebox.showinfo("Success", f"Merged PDF saved:\n{output_file}")

    # ==========================================================
    # EDIT PAGES (re-order, rotate, delete, split, extract)
    # ==========================================================

    def build_pages_frame(self, frame):
        self.section_title(frame, "Edit pages",
                           "Drag pages into a new order, rotate or delete them, then save all, a selection, or split into several PDFs.")
        self.pages_title, self.pages_info, tools = self.toolbar(frame, "＋  Add PDF", self.select_pages_file)
        self.pages_title.configure(text="No PDF selected")
        self.pages_info.configure(text="Adding a second PDF puts its pages at the end")

        ctk.CTkLabel(tools, text="All pages", font=font(12), text_color=MUTED).pack(side="left", padx=(0, 8))
        symbol_button(tools, "↺", lambda: self.pages_grid.rotate_all(-90)).pack(side="left", padx=2)
        symbol_button(tools, "↻", lambda: self.pages_grid.rotate_all(90)).pack(side="left", padx=2)
        small_button(tools, "⇄  Reverse", lambda: self.pages_grid.reverse(), width=80,
                     font_=ctk.CTkFont(family=SYMBOL_FONT, size=13)).pack(side="left", padx=(8, 2))
        small_button(tools, "Reset", self.reset_pages, width=56).pack(side="left", padx=2)
        small_button(tools, "Clear", self.clear_pages, width=56).pack(side="left", padx=2)

        bar, self.pages_summary = self.bottom_bar(frame)
        primary_button(bar, "Save PDF", self.save_pages, width=200, height=48).pack(side="right")
        self.pages_output = SlideToggle(bar, [ONE_PDF, EVERY_PAGE, CUSTOM_SPLIT], command=self.on_pages_output_change)
        self.pages_output.pack(side="right", padx=16)

        # Extra row for "Custom split", only visible when that option is chosen
        self.custom_holder = tk.Frame(frame, bg=CARD, height=0)
        self.custom_holder.pack(side="bottom", fill="x", padx=28)
        self.custom_row = ctk.CTkFrame(self.custom_holder, fg_color=SUBCARD, corner_radius=12)
        ctk.CTkLabel(self.custom_row, text="Pages per PDF", font=font(13, "bold"), text_color=TEXT).pack(side="left", padx=(16, 10), pady=10)
        self.custom_entry = ctk.CTkEntry(self.custom_row, height=34, width=260, corner_radius=10, font=font(13),
                                         border_color=BORDER, placeholder_text="e.g. 1-3; 4-end")
        self.custom_entry.pack(side="left")
        self.custom_entry.bind("<KeyRelease>", lambda event: self.update_pages_summary())
        ctk.CTkLabel(self.custom_row, text="Use the page numbers shown on the tiles.  ';' starts a new PDF.  "
                                           "Pages you leave out are not saved.",
                     font=font(12), text_color=MUTED).pack(side="left", padx=12)

        self.pages_grid = TileGrid(
            frame, "Add a PDF to see its pages here.\nYou can also drag a PDF from Explorer into this window.",
            on_change=self.update_pages_summary, rotatable=True,
        )
        self.pages_grid.pack(fill="both", expand=True, padx=20, pady=(10, 0))

    def select_pages_file(self):
        files = filedialog.askopenfilenames(title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        if files:
            self.add_pages_files(files)

    def add_pages_files(self, files):
        failed = []

        def load():
            for file in files:
                path = Path(file)
                try:
                    thumbs = page_thumbnails(path)
                except Exception:
                    failed.append(path.name)
                    continue
                for index, thumb in enumerate(thumbs):
                    self.pages_original.append((path, index, thumb))
                    self.pages_grid.add(self._page_item(path, index, thumb))

        self.run_busy("Edit pages", load)
        self._update_page_subtitles()
        self.pages_grid.refresh()
        if failed:
            messagebox.showwarning("Edit pages", "These files could not be opened as PDF:\n\n" + "\n".join(failed))

    @staticmethod
    def _page_item(path, index, thumb):
        return {"source": path, "index": index, "thumb": thumb, "title": f"Page {index + 1}"}

    def _sources(self):
        return list(dict.fromkeys(source for source, _, _ in self.pages_original))

    def _update_page_subtitles(self):
        """With pages from several PDFs, show on each tile which file it comes from."""
        several = len(self._sources()) > 1
        for item in self.pages_grid.items:
            stem = item["source"].stem
            subtitle = (stem if len(stem) <= 14 else stem[:13] + "…") if several else ""
            if item.get("subtitle", "") != subtitle:
                item["subtitle"] = subtitle
                self.pages_grid.update_tile(item)

    def reset_pages(self):
        """Back to the pages as loaded: original order, no rotation, nothing deleted."""
        if not self.pages_original: return
        self.pages_grid.clear()
        for path, index, thumb in self.pages_original:
            self.pages_grid.add(self._page_item(path, index, thumb))
        self._update_page_subtitles()
        self.pages_grid.refresh()

    def clear_pages(self):
        self.pages_original = []
        self.pages_grid.clear()

    def on_pages_output_change(self, value):
        if value == CUSTOM_SPLIT:
            self.custom_row.pack(fill="x", pady=(8, 0))
            self.custom_entry.focus_set()
        else:
            self.custom_row.pack_forget()
        self.update_pages_summary()

    def _page_groups(self):
        """List of page-number groups (1-based positions), one group per output PDF."""
        count = len(self.pages_grid.items)
        mode = self.pages_output.get()
        if mode == ONE_PDF:
            return [list(range(1, count + 1))]
        if mode == EVERY_PAGE:
            return [[n] for n in range(1, count + 1)]
        return parse_page_groups(self.custom_entry.get(), count)

    def update_pages_summary(self):
        items = self.pages_grid.items
        sources = self._sources()
        if sources:
            name = sources[0].name + (f"  (+{plural(len(sources) - 1, 'more file')})" if len(sources) > 1 else "")
            self.pages_title.configure(text=name)
        else:
            self.pages_title.configure(text="No PDF selected")

        if not items:
            self.pages_summary.configure(text="")
            return

        rotated = sum(1 for item in items if item["angle"])
        removed = len(self.pages_original) - len(items)
        details = []
        if rotated:
            details.append(f"{rotated} rotated")
        if removed > 0:
            details.append(f"{removed} deleted")
        details = f"   ({', '.join(details)})" if details else ""

        try:
            groups = self._page_groups()
        except ValueError as error:
            text = "Enter pages like 1-3; 4-end" if not self.custom_entry.get().strip() else str(error)
            self.pages_summary.configure(text=text, text_color=RED)
            return

        if len(groups) == 1:
            pages = len(groups[0])
            text = f"1 PDF with {plural(pages, 'page')}" + details
        else:
            parts = " · ".join(format_page_ranges(group) for group in groups[:6])
            more = " · …" if len(groups) > 6 else ""
            text = f"{len(groups)} PDFs: {parts}{more}" + details
        self.pages_summary.configure(text=text, text_color=GREEN if (rotated or removed > 0) else MUTED)

    def save_pages(self):
        items = self.pages_grid.items
        if not items:
            messagebox.showwarning("Edit pages", "Add a PDF first.")
            return
        try:
            groups = self._page_groups()
        except ValueError as error:
            messagebox.showwarning("Edit pages", str(error))
            return

        stem = items[0]["source"].stem
        folder = items[0]["source"].parent
        page_groups = [[(items[n - 1]["source"], items[n - 1]["index"], items[n - 1]["angle"]) for n in group]
                       for group in groups]
        mode = self.pages_output.get()

        if len(groups) == 1:
            default = f"{stem}-edited.pdf" if mode == ONE_PDF else f"{stem}_pages_{format_page_ranges(groups[0])}.pdf"
            output_file = filedialog.asksaveasfilename(
                title="Save PDF", initialdir=folder, initialfile=default,
                defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
            )
            if not output_file: return
            if self.run_busy("Edit pages", lambda: write_pages(page_groups[0], output_file)) is None: return
            self.set_status(f"✔  Saved: {output_file}")
            messagebox.showinfo("Success", f"Saved:\n{output_file}")
            return

        output_folder = filedialog.askdirectory(title=f"Folder for the {len(groups)} PDF files", initialdir=folder)
        if not output_folder: return
        output_folder = Path(output_folder)

        output_files = []
        for group in groups:
            name = (f"{stem}_page_{group[0]:03d}.pdf" if mode == EVERY_PAGE
                    else f"{stem}_pages_{format_page_ranges(group)}.pdf")
            output_files.append(unique_path(output_folder / name, output_files))

        if self.run_busy("Edit pages", lambda: write_page_groups(page_groups, output_files)) is None: return
        self.set_status(f"✔  {len(output_files)} PDF files saved to: {output_folder}")
        messagebox.showinfo("Success", f"{len(output_files)} PDF files saved to:\n{output_folder}")

    # ==========================================================
    # IMAGE TO PDF
    # ==========================================================

    def build_image_frame(self, frame):
        self.section_title(frame, "Image to PDF",
                           "Turn photos, scans and screenshots into PDF. Rotate them and drag them into the right order first.")
        self.image_title, self.image_info, tools = self.toolbar(frame, "＋  Add images", self.select_images)
        self.image_title.configure(text="No images selected")
        types = ", ".join(ext.lstrip(".").upper() for ext in IMAGE_EXTENSIONS if ext not in (".jpeg", ".jfif", ".tiff", ".heif"))
        self.image_info.configure(text=f"Supported: {types}")

        ctk.CTkLabel(tools, text="All images", font=font(12), text_color=MUTED).pack(side="left", padx=(0, 8))
        symbol_button(tools, "↺", lambda: self.image_grid.rotate_all(-90)).pack(side="left", padx=2)
        symbol_button(tools, "↻", lambda: self.image_grid.rotate_all(90)).pack(side="left", padx=2)
        small_button(tools, "Clear", lambda: self.image_grid.clear(), width=60).pack(side="left", padx=(8, 0))

        bar, self.image_summary = self.bottom_bar(frame)
        primary_button(bar, "Convert to PDF", self.save_images_as_pdf, width=220, height=48).pack(side="right")
        self.image_output = SlideToggle(bar, [IMAGES_COMBINED, IMAGES_SEPARATE],
                                        command=lambda value: self.update_image_summary())
        self.image_output.pack(side="right", padx=16)

        self.image_grid = TileGrid(
            frame, "Add one or more images to get started.\nYou can also drag them from Explorer into this window.",
            on_change=self.update_image_summary, rotatable=True, stacked=True,
        )
        self.image_grid.pack(fill="both", expand=True, padx=20, pady=(10, 0))

    def select_images(self):
        patterns = " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS)
        files = filedialog.askopenfilenames(title="Select images", filetypes=[("Images", patterns), ("All files", "*.*")])
        if files:
            self.add_image_files(files)

    def add_image_files(self, files):
        failed = []

        def load():
            for file in files:
                path = Path(file)
                try:
                    item = {"path": path, "title": path.name, "thumb": thumbnail(path), "pages": page_count(path)}
                except Exception:
                    failed.append(path.name)
                    continue
                self.image_grid.add(item)

        self.run_busy("Image to PDF", load)
        self.image_grid.refresh()
        if failed:
            messagebox.showwarning("Image to PDF", "These files could not be opened as an image:\n\n" + "\n".join(failed))

    def update_image_summary(self):
        items = self.image_grid.items
        self.image_title.configure(text=f"{plural(len(items), 'image')} selected" if items else "No images selected")
        if not items:
            self.image_summary.configure(text="")
            return
        if self.image_output.get() == IMAGES_COMBINED:
            pages = sum(item["pages"] for item in items)
            text = f"1 PDF with {plural(pages, 'page')}, in the order shown."
        else:
            text = f"{len(items)} separate PDF{'s' if len(items) != 1 else ''}, one per image."
        self.image_summary.configure(text=text)

    def save_images_as_pdf(self):
        items = self.image_grid.items
        if not items:
            messagebox.showwarning("Image to PDF", "Add at least one image first.")
            return

        paths = [item["path"] for item in items]
        rotations = [item["angle"] for item in items]
        first = paths[0]

        if self.image_output.get() == IMAGES_COMBINED:
            default = f"{first.stem}-converted.pdf" if len(paths) == 1 else f"{first.stem}-and-{len(paths) - 1}-more-converted.pdf"
            output_file = filedialog.asksaveasfilename(
                title="Save PDF", initialdir=first.parent, initialfile=default,
                defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
            )
            if not output_file: return
            if self.run_busy("Image to PDF", lambda: imagetopdf(paths, output_file, rotations)) is None: return
            self.set_status(f"✔  PDF saved: {output_file}")
            messagebox.showinfo("Success", f"PDF saved:\n{output_file}")
        else:
            output_folder = filedialog.askdirectory(title="Folder for the PDF files", initialdir=first.parent)
            if not output_folder: return
            created = self.run_busy("Image to PDF", lambda: imagestopdfs(paths, output_folder, rotations))
            if created is None: return
            self.set_status(f"✔  {len(created)} PDF files saved to: {output_folder}")
            messagebox.showinfo("Success", f"{len(created)} PDF files saved to:\n{output_folder}")

    # ==========================================================
    # DRAG FILES IN FROM EXPLORER
    # ==========================================================

    def setup_file_drop(self):
        if not getattr(self.root, "dnd_available", False):
            return
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<DropEnter>>", self._on_drop_enter)
        self.root.dnd_bind("<<DropLeave>>", self._on_drop_leave)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop_enter(self, event):
        self.mode_frames[self.current_mode()].configure(border_color=GREEN, border_width=3)
        self.set_status("Drop the files to add them")
        return event.action

    def _on_drop_leave(self, event):
        self.mode_frames[self.current_mode()].configure(border_color=BORDER, border_width=1)
        self.set_status("")
        return event.action

    def _on_drop(self, event):
        self._on_drop_leave(event)
        self.handle_dropped_files(self.root.tk.splitlist(event.data))
        return event.action

    def handle_dropped_files(self, paths):
        """
        PDFs go to the current screen (or Merge PDF when you're on Image to PDF),
        images always go to Image to PDF. Folders are opened (not their sub-folders).
        """
        files = []
        for path in map(Path, paths):
            if path.is_dir():
                files.extend(sorted((p for p in path.iterdir() if p.is_file()), key=natural_key))
            elif path.is_file():
                files.append(path)

        pdfs = [f for f in files if is_pdf(f)]
        images = [f for f in files if is_image(f)]
        ignored = [f.name for f in files if not is_pdf(f) and not is_image(f)]

        messages = []
        if pdfs:
            target = self.current_mode() if self.current_mode() in ("Merge PDF", "Edit Pages") else "Merge PDF"
            self.show_mode(target)
            if target == "Merge PDF":
                self.add_merge_files(pdfs)
            else:
                self.add_pages_files(pdfs)
            messages.append(f"{plural(len(pdfs), 'PDF')} added to {target}")
        if images:
            if not pdfs:
                self.show_mode("Image to PDF")
            self.add_image_files(images)
            messages.append(f"{plural(len(images), 'image')} added to Image to PDF")

        if messages:
            self.set_status("✔  " + ";  ".join(messages))
        if ignored:
            shown = "\n".join(ignored[:15]) + ("\n…" if len(ignored) > 15 else "")
            messagebox.showwarning("Not added", "These files are not a PDF or a supported image:\n\n" + shown)

    def run(self):
        if not has_real_previews():
            self.set_status("Tip: install 'pymupdf' to see real page previews")
        self.root.mainloop()
