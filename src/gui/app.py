import os
import re
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from src.convert.imagetopdf import imagetopdf, imagestopdfs, thumbnail, page_count, IMAGE_EXTENSIONS
from src.modify.organize import write_pages, write_page_groups, unique_path
from src.utils.page_ranges import parse_page_groups, format_page_ranges
from src.utils.thumbnails import page_thumbnails, has_real_previews
from src.gui.widgets import (
    BG, CARD, SUBCARD, BORDER, GREEN, NAVY, TEXT, MUTED, RED, GREEN_LIGHT, GREEN_HOVER,
    LIGHT_FONT, SYMBOL_FONT,
    font, heading, primary_button, secondary_button, small_button, symbol_button, card, plural,
    SlideToggle, TileGrid,
)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    TkinterDnD = None


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

PDF_MODE = "Merge & Edit PDF"
IMAGE_MODE = "Image to PDF"
MODES = [PDF_MODE, IMAGE_MODE]

FILES_VIEW = "Files"
PAGES_VIEW = "Pages"

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
    """Sort key that puts 'page2' before 'page10' (like Explorer does)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(path).name)]


def sorted_paths(paths):
    return sorted((Path(p) for p in paths), key=natural_key)


def is_pdf(path):
    return Path(path).suffix.lower() == ".pdf"


def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def short_names(stems):
    """
    Short labels that tell files apart: the shared beginning is left out.
    ["Stippie en Jan, page01", "Stippie en Jan, page02"] -> ["page01", "page02"]
    """
    stems = list(dict.fromkeys(stems))
    labels = {}
    for stem in stems:
        # longest beginning this name shares with any other name
        shared = max((len(os.path.commonprefix([stem, other])) for other in stems if other != stem), default=0)
        prefix = stem[:shared]
        # cut back to the start of a word, so "page01" stays readable
        cut = max(prefix.rfind(char) for char in " ,_-.") + 1 if prefix else 0
        label = stem[cut:].strip(" ,_-.") or stem
        labels[stem] = label if len(label) <= 16 else "…" + label[-15:]
    return labels


class PDFToolApp:

    def __init__(self):
        self.root = AppWindow(fg_color=BG)

        self.root.iconbitmap(Path("images/logoTU_icon.ico"))
        self.root.title("Transform PDF")
        self.root.geometry("1200x760")
        self.root.minsize(1100, 660)

        self.mode_frames = {}
        self.pages_original = []     # page dicts as loaded (for Reset)
        self.page_counts = {}        # source path -> number of pages in that file
        self.pdf_view = PAGES_VIEW

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

        for mode, builder in ((PDF_MODE, self.build_pdf_frame), (IMAGE_MODE, self.build_image_frame)):
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
            text_color=TEXT, dynamic_resizing=False, width=380,
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
        secondary_button(bar, button_text, command, width=170).pack(side="left", padx=14, pady=14)
        tools = ctk.CTkFrame(bar, fg_color="transparent")
        tools.pack(side="right", padx=14)   # packed before the text, so the tools never get squeezed
        text = ctk.CTkFrame(bar, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        title = ctk.CTkLabel(text, text="", font=font(13, "bold"), text_color=TEXT, anchor="w")
        title.pack(anchor="w")
        info = ctk.CTkLabel(text, text="", font=font(12), text_color=MUTED, anchor="w", height=16)
        info.pack(anchor="w")
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
    # MERGE & EDIT PDF
    # ==========================================================
    #
    # The pages are the heart of this screen: one list of page dicts
    #   {"source": Path, "index": 0-based page number, "thumb": PIL image, "angle": 0/90/180/270}
    # It can be shown in two ways:
    #   - Pages view: one tile per page
    #   - Files view: one tile per file (pages that follow each other and come
    #     from the same file), handy for merging. Moving, rotating or deleting
    #     a file tile does that for all its pages.

    def build_pdf_frame(self, frame):
        self.section_title(frame, "Merge & edit PDF",
                           "Add one or more PDFs. Drag files or pages into the right order, rotate or delete them, then save.")
        self.pdf_title, self.pdf_info, tools = self.toolbar(frame, "＋  Add PDF files", self.select_pdf_files)
        self.pdf_title.configure(text="No PDF selected")
        self.pdf_info.configure(text="Tip: you can also drag PDF files into this window")

        ctk.CTkLabel(tools, text="Show", font=font(12), text_color=MUTED).pack(side="left", padx=(0, 6))
        self.view_toggle = SlideToggle(tools, [FILES_VIEW, PAGES_VIEW], command=self.set_view, height=32, bg=SUBCARD)
        self.view_toggle.set(PAGES_VIEW)
        self.view_toggle.pack(side="left", padx=(0, 14))
        symbol_button(tools, "↺", lambda: self.pdf_grid.rotate_all(-90)).pack(side="left", padx=2)
        symbol_button(tools, "↻", lambda: self.pdf_grid.rotate_all(90)).pack(side="left", padx=2)
        small_button(tools, "⇄  Reverse", lambda: self.pdf_grid.reverse(), width=80,
                     font_=ctk.CTkFont(family=SYMBOL_FONT, size=13)).pack(side="left", padx=(8, 2))
        small_button(tools, "Reset", self.reset_pdf, width=56).pack(side="left", padx=2)
        small_button(tools, "Clear", self.clear_pdf, width=56).pack(side="left", padx=2)

        bar, self.pdf_summary = self.bottom_bar(frame)
        primary_button(bar, "Save PDF", self.save_pdf, width=200, height=48).pack(side="right")
        self.pdf_output = SlideToggle(bar, [ONE_PDF, EVERY_PAGE, CUSTOM_SPLIT], command=self.on_pdf_output_change)
        self.pdf_output.pack(side="right", padx=16)

        # Extra row for "Custom split", only visible when that option is chosen
        self.custom_holder = tk.Frame(frame, bg=CARD, height=0)
        self.custom_holder.pack(side="bottom", fill="x", padx=28)
        self.custom_row = ctk.CTkFrame(self.custom_holder, fg_color=SUBCARD, corner_radius=12)
        ctk.CTkLabel(self.custom_row, text="Pages per PDF", font=font(13, "bold"), text_color=TEXT).pack(side="left", padx=(16, 10), pady=10)
        self.custom_entry = ctk.CTkEntry(self.custom_row, height=34, width=260, corner_radius=10, font=font(13),
                                         border_color=BORDER, placeholder_text="e.g. 1-3; 4-end")
        self.custom_entry.pack(side="left")
        self.custom_entry.bind("<KeyRelease>", lambda event: self.update_pdf_summary())
        ctk.CTkLabel(self.custom_row, text="Page numbers as shown in Pages view.  ';' starts a new PDF.  "
                                           "Pages you leave out are not saved.",
                     font=font(12), text_color=MUTED).pack(side="left", padx=12)

        self.pdf_grid = TileGrid(
            frame, "Add one or more PDF files to get started.\nYou can also drag them from Explorer into this window.",
            on_change=self.update_pdf_summary, rotatable=True, stacked=True,
        )
        self.pdf_grid.pack(fill="both", expand=True, padx=20, pady=(10, 0))

    # ---------- the page list ----------

    def current_pages(self):
        """The pages in their current order and rotation, whatever the view."""
        if self.pdf_view == PAGES_VIEW:
            return [self._page(item, item["angle"]) for item in self.pdf_grid.items]
        pages = []
        for item in self.pdf_grid.items:
            delta = item["angle"] - item["base_angle"]
            pages.extend(self._page(page, page["angle"] + delta) for page in item["run"])
        return pages

    @staticmethod
    def _page(page, angle):
        return {"source": page["source"], "index": page["index"], "thumb": page["thumb"], "angle": angle % 360}

    def show_pages(self, pages, view=None):
        """Fill the grid with these pages, in the given (or current) view."""
        if view is not None and view != self.pdf_view:
            self.pdf_view = view
            if self.view_toggle.get() != view:
                self.view_toggle.set(view, animate=True)
        self.pdf_grid.clear()
        if self.pdf_view == PAGES_VIEW:
            for page in pages:
                self.pdf_grid.add(dict(page, title=f"Page {page['index'] + 1}"))
        else:
            for run in self._runs(pages):
                first = run[0]
                self.pdf_grid.add({
                    "run": run, "source": first["source"], "thumb": first["thumb"],
                    "angle": first["angle"], "base_angle": first["angle"],
                    "pages": len(run), "title": first["source"].name,
                })
        self._update_labels()
        self.pdf_grid.refresh()

    @staticmethod
    def _runs(pages):
        """Group pages that follow each other and come from the same file."""
        runs = []
        for page in pages:
            if runs and runs[-1][-1]["source"] == page["source"]:
                runs[-1].append(page)
            else:
                runs.append([page])
        return runs

    def _update_labels(self):
        """Titles, short subtitles and tooltips of the tiles."""
        sources = list(dict.fromkeys(item["source"] for item in self.pdf_grid.items))
        names = short_names(source.stem for source in sources)
        several = len(sources) > 1
        position = 1
        for item in self.pdf_grid.items:
            source = item["source"]
            total = self.page_counts.get(source, 0)
            if "run" in item:
                count = len(item["run"])
                first, last = item["run"][0]["index"] + 1, item["run"][-1]["index"] + 1
                subtitle = f"p. {position}" if count == 1 else f"p. {position}-{position + count - 1}"
                tooltip = f"{source.name}\n{plural(count, 'page')}" + (
                    "" if count == total else f" (page {first}-{last} of {total})")
                position += count
            else:
                title = f"Page {item['index'] + 1}"
                subtitle = names[source.stem] if several else ""
                tooltip = f"{source.name}\nPage {item['index'] + 1} of {total}"
                if item.get("title") != title:
                    item["title"] = title
                position += 1
            changed = item.get("subtitle") != subtitle or item.get("tooltip") != tooltip
            item["subtitle"], item["tooltip"] = subtitle, tooltip
            if changed and "frame" in item:
                self.pdf_grid.update_tile(item)

    # ---------- actions ----------

    def select_pdf_files(self):
        files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if files:
            self.add_pdf_files(files)

    def add_pdf_files(self, files):
        files = sorted_paths(files)
        was_empty = not self.pdf_grid.items
        new_pages, failed = [], []

        def load():
            for path in files:
                try:
                    thumbs = page_thumbnails(path)
                except Exception:
                    failed.append(path.name)
                    continue
                self.page_counts[path] = len(thumbs)
                for index, thumb in enumerate(thumbs):
                    new_pages.append({"source": path, "index": index, "thumb": thumb, "angle": 0})

        self.run_busy("Merge & edit PDF", load)
        if new_pages:
            self.pages_original.extend(dict(page) for page in new_pages)
            # Several files: start with one tile per file; a single file: show its pages
            view = (FILES_VIEW if len(files) - len(failed) > 1 else PAGES_VIEW) if was_empty else None
            self.show_pages(self.current_pages() + new_pages, view)
        if failed:
            messagebox.showwarning("Merge & edit PDF", "These files could not be opened as PDF:\n\n" + "\n".join(failed))

    def set_view(self, view):
        self.show_pages(self.current_pages(), view)

    def reset_pdf(self):
        """Back to the pages as loaded: original order, no rotation, nothing deleted."""
        if self.pages_original:
            self.show_pages([dict(page) for page in self.pages_original])

    def clear_pdf(self):
        self.pages_original = []
        self.page_counts = {}
        self.pdf_grid.clear()

    def on_pdf_output_change(self, value):
        if value == CUSTOM_SPLIT:
            self.custom_row.pack(fill="x", pady=(8, 0))
            self.custom_entry.focus_set()
        else:
            self.custom_row.pack_forget()
        self.update_pdf_summary()

    def _page_groups(self, count):
        """List of page-number groups (1-based positions), one group per output PDF."""
        mode = self.pdf_output.get()
        if mode == ONE_PDF:
            return [list(range(1, count + 1))]
        if mode == EVERY_PAGE:
            return [[n] for n in range(1, count + 1)]
        return parse_page_groups(self.custom_entry.get(), count)

    def update_pdf_summary(self):
        if self.pdf_view == FILES_VIEW:
            self._update_labels()   # page numbers on the file tiles change when files move
        pages = self.current_pages()
        sources = list(dict.fromkeys(page["source"] for page in self.pages_original))
        if sources:
            more = f"  (+{plural(len(sources) - 1, 'more file')})" if len(sources) > 1 else ""
            self.pdf_title.configure(text=sources[0].name + more)
        else:
            self.pdf_title.configure(text="No PDF selected")

        if not pages:
            self.pdf_summary.configure(text="")
            return

        rotated = sum(1 for page in pages if page["angle"])
        removed = len(self.pages_original) - len(pages)
        details = [f"{rotated} rotated"] if rotated else []
        if removed > 0:
            details.append(f"{removed} deleted")
        details = f"   ({', '.join(details)})" if details else ""

        try:
            groups = self._page_groups(len(pages))
        except ValueError as error:
            text = "Enter pages like 1-3; 4-end" if not self.custom_entry.get().strip() else str(error)
            self.pdf_summary.configure(text=text, text_color=RED)
            return

        if len(groups) == 1:
            text = f"1 PDF with {plural(len(groups[0]), 'page')}" + details
        else:
            parts = " · ".join(format_page_ranges(group) for group in groups[:6])
            more = " · …" if len(groups) > 6 else ""
            text = f"{len(groups)} PDFs: {parts}{more}" + details
        self.pdf_summary.configure(text=text, text_color=GREEN if (rotated or removed > 0) else MUTED)

    def save_pdf(self):
        pages = self.current_pages()
        if not pages:
            messagebox.showwarning("Merge & edit PDF", "Add a PDF first.")
            return
        try:
            groups = self._page_groups(len(pages))
        except ValueError as error:
            messagebox.showwarning("Merge & edit PDF", str(error))
            return

        first = pages[0]["source"]
        several_sources = len({page["source"] for page in pages}) > 1
        page_groups = [[(pages[n - 1]["source"], pages[n - 1]["index"], pages[n - 1]["angle"]) for n in group]
                       for group in groups]
        mode = self.pdf_output.get()

        if len(groups) == 1:
            if mode == ONE_PDF:
                default = f"{first.stem}-merged.pdf" if several_sources else f"{first.stem}-edited.pdf"
            else:
                default = f"{first.stem}_pages_{format_page_ranges(groups[0])}.pdf"
            output_file = filedialog.asksaveasfilename(
                title="Save PDF", initialdir=first.parent, initialfile=default,
                defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")]
            )
            if not output_file: return
            if self.run_busy("Save PDF", lambda: write_pages(page_groups[0], output_file)) is None: return
            self.set_status(f"✔  Saved: {output_file}")
            messagebox.showinfo("Success", f"Saved:\n{output_file}")
            return

        output_folder = filedialog.askdirectory(title=f"Folder for the {len(groups)} PDF files", initialdir=first.parent)
        if not output_folder: return
        output_folder = Path(output_folder)

        output_files = []
        for group in groups:
            if mode == EVERY_PAGE:
                page = pages[group[0] - 1]
                name = f"{page['source'].stem}_page_{page['index'] + 1:03d}.pdf"
            else:
                name = f"{first.stem}_pages_{format_page_ranges(group)}.pdf"
            output_files.append(unique_path(output_folder / name, output_files))

        if self.run_busy("Save PDF", lambda: write_page_groups(page_groups, output_files)) is None: return
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
            for path in sorted_paths(files):
                try:
                    item = {"path": path, "title": path.name, "tooltip": f"{path.name}\n{path.parent}",
                            "thumb": thumbnail(path), "pages": page_count(path)}
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
        PDFs go to Merge & Edit PDF, images to Image to PDF.
        Folders are opened (not their sub-folders). Files are added in
        alphabetical order, whichever file you started dragging.
        """
        files = []
        for path in map(Path, paths):
            if path.is_dir():
                files.extend(p for p in path.iterdir() if p.is_file())
            elif path.is_file():
                files.append(path)
        files = sorted_paths(files)

        pdfs = [f for f in files if is_pdf(f)]
        images = [f for f in files if is_image(f)]
        ignored = [f.name for f in files if not is_pdf(f) and not is_image(f)]

        messages = []
        if pdfs:
            self.show_mode(PDF_MODE)
            self.add_pdf_files(pdfs)
            messages.append(f"{plural(len(pdfs), 'PDF')} added")
        if images:
            if not pdfs:
                self.show_mode(IMAGE_MODE)
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
