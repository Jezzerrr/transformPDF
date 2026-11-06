"""
Shared look and building blocks for the GUI:
- colours, fonts and button helpers
- SlideToggle: a switch with a sliding knob (drag it or click an option)
- TileGrid: a grid of page/image tiles that can be rotated, removed and
  re-ordered by dragging
"""
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from src.utils.thumbnails import PREVIEW_BG


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
RED = "#B42318"

HEADING_FONT = "Bahnschrift SemiBold"
LIGHT_FONT = "Bahnschrift Light"
BODY_FONT = "Segoe UI Variable Text"
SYMBOL_FONT = "Segoe UI Symbol"

TILE_WIDTH = 160
TILE_PAD = 7
PREVIEW_BOX = 132        # max size of a preview inside a tile


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


def small_button(parent, text, command, width=34, font_=None, text_color=TEXT):
    return ctk.CTkButton(
        parent, text=text, command=command, width=width, height=30, corner_radius=8,
        fg_color=SUBCARD, hover_color=GREEN_LIGHT, text_color=text_color,
        font=font_ or font(13),
    )


def symbol_button(parent, text, command, size=17, color=GREEN):
    """Small square button with a symbol such as ↺ ↻ ◀ ▶."""
    return small_button(parent, text, command, font_=ctk.CTkFont(family=SYMBOL_FONT, size=size), text_color=color)


def card(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER, **kwargs)


def plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


# ==========================================================
# SLIDE TOGGLE
# ==========================================================

def _rounded_image(width, height, radius, fill, outline=None, scale=4):
    """Anti-aliased rounded rectangle as a PIL image (drawn big, then scaled down)."""
    big = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    draw.rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1], radius=radius * scale,
        fill=fill, outline=outline, width=scale if outline else 0,
    )
    return big.resize((width, height), Image.LANCZOS)


class SlideToggle(tk.Canvas):
    """
    A switch with a sliding knob. Click an option, or grab the knob and drag
    it to another option; it snaps into place when you let go.
    """

    def __init__(self, master, values, command=None, height=38, bg=CARD):
        self.scaling = ctk.ScalingTracker.get_widget_scaling(master)
        self.values = list(values)
        self.command = command
        self.index = 0

        self.text_font = tkfont.Font(family=BODY_FONT, size=-int(13 * self.scaling), weight="bold")
        self.pad = int(4 * self.scaling)
        text_width = max(self.text_font.measure(value) for value in self.values)
        self.segment = text_width + int(32 * self.scaling)
        self.h = int(height * self.scaling)
        self.w = self.segment * len(self.values) + 2 * self.pad

        super().__init__(master, width=self.w, height=self.h, bg=bg, highlightthickness=0, cursor="hand2")

        knob_h = self.h - 2 * self.pad
        self._track_img = ImageTk.PhotoImage(_rounded_image(self.w, self.h, self.h // 2, SUBCARD, BORDER))
        self._knob_img = ImageTk.PhotoImage(_rounded_image(self.segment, knob_h, knob_h // 2, NAVY))
        self.create_image(0, 0, image=self._track_img, anchor="nw")
        self.knob = self.create_image(self._knob_x(0), self.pad, image=self._knob_img, anchor="nw")
        self.labels = [
            self.create_text(self._knob_x(i) + self.segment / 2, self.h / 2, text=value, font=self.text_font)
            for i, value in enumerate(self.values)
        ]
        self._color_labels(0)

        self._press_x = None
        self._knob_start = None
        self._dragging = False
        self._animation = None
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_motion)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _knob_x(self, index):
        return self.pad + index * self.segment

    def _nearest(self, knob_x):
        return min(range(len(self.values)), key=lambda i: abs(self._knob_x(i) - knob_x))

    def _color_labels(self, active):
        for i, label in enumerate(self.labels):
            self.itemconfigure(label, fill="white" if i == active else TEXT)

    def get(self):
        return self.values[self.index]

    def set(self, value, animate=False):
        self._select(self.values.index(value), animate=animate, notify=False)

    def _select(self, index, animate=True, notify=True):
        changed = index != self.index
        self.index = index
        self._color_labels(index)
        if animate:
            self._animate_to(self._knob_x(index))
        else:
            self.coords(self.knob, self._knob_x(index), self.pad)
        if changed and notify and self.command:
            self.command(self.get())

    def _animate_to(self, target, steps=8):
        if self._animation:
            self.after_cancel(self._animation)
        start = self.coords(self.knob)[0]

        def step(n=1):
            t = n / steps
            eased = 1 - (1 - t) ** 3
            self.coords(self.knob, start + (target - start) * eased, self.pad)
            if n < steps:
                self._animation = self.after(12, step, n + 1)
            else:
                self._animation = None
        step()

    def _on_press(self, event):
        self._press_x = event.x
        self._knob_start = self.coords(self.knob)[0]
        self._dragging = False

    def _on_motion(self, event):
        if self._press_x is None:
            return
        if not self._dragging and abs(event.x - self._press_x) > 3:
            self._dragging = True
        if self._dragging:
            x = self._knob_start + (event.x - self._press_x)
            x = max(self._knob_x(0), min(self._knob_x(len(self.values) - 1), x))
            self.coords(self.knob, x, self.pad)
            self._color_labels(self._nearest(x))

    def _on_release(self, event):
        if self._press_x is None:
            return
        if self._dragging:
            index = self._nearest(self.coords(self.knob)[0])
        else:
            index = max(0, min(len(self.values) - 1, int((event.x - self.pad) // self.segment)))
        self._press_x = None
        self._dragging = False
        self._select(index)


# ==========================================================
# TOOLTIP
# ==========================================================

class Tooltip:
    """Small pop-up text that appears when the mouse rests on a widget."""

    def __init__(self, root):
        self.root = root
        self.window = None
        self._show_job = None
        self._hide_job = None

    def attach(self, widget, text_func):
        """text_func() returns the text to show (so it can change over time)."""
        widget.bind("<Enter>", lambda event: self._enter(text_func), add="+")
        widget.bind("<Leave>", lambda event: self._leave(), add="+")
        widget.bind("<ButtonPress>", lambda event: self.hide(), add="+")

    def _enter(self, text_func):
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        if self.window is None and self._show_job is None:
            self._show_job = self.root.after(450, lambda: self._show(text_func()))

    def _leave(self):
        if self._show_job:
            self.root.after_cancel(self._show_job)
            self._show_job = None
        # small delay: moving between the parts of one widget fires Leave + Enter
        self._hide_job = self.root.after(60, self.hide)

    def _show(self, text):
        self._show_job = None
        if not text:
            return
        x, y = self.root.winfo_pointerx() + 14, self.root.winfo_pointery() + 18
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        tk.Label(self.window, text=text, justify="left", bg="#1F2937", fg="white", padx=10, pady=6,
                 font=(BODY_FONT, 10)).pack()
        self.window.geometry(f"+{x}+{y}")

    def hide(self):
        for job in (self._show_job, self._hide_job):
            if job:
                self.root.after_cancel(job)
        self._show_job = self._hide_job = None
        if self.window is not None:
            self.window.destroy()
            self.window = None


# ==========================================================
# TILE GRID
# ==========================================================

def preview_image(thumb, angle=0, pages=1, stacked=False):
    """
    Turn a thumbnail into the picture shown on a tile: rotated, with a thin
    border, and drawn as a small stack of paper when it has several pages.
    """
    image = thumb.rotate(-angle, expand=True) if angle else thumb.copy()
    image = image.convert("RGB")
    ImageDraw.Draw(image).rectangle([0, 0, image.width - 1, image.height - 1], outline="#C9D3E3", width=2)

    layers = 0 if not stacked or pages < 2 else (1 if pages == 2 else 2)
    if not layers:
        return image

    offset = max(8, int(max(image.size) * 0.06))
    width, height = image.width + layers * offset, image.height + layers * offset
    stack = Image.new("RGB", (width, height), PREVIEW_BG)
    draw = ImageDraw.Draw(stack)
    # Sheets behind the first page, shifted up and to the right
    for layer in range(layers, 0, -1):
        x, y = layer * offset, (layers - layer) * offset
        shade = "#FFFFFF" if layer == 1 else "#F7F9FC"
        draw.rectangle([x, y, x + image.width - 1, y + image.height - 1], fill=shade, outline="#B9C6DA", width=2)
    stack.paste(image, (0, layers * offset))
    return stack


class TileGrid(ctk.CTkScrollableFrame):
    """
    Scrollable grid of tiles. Every item is a dict with at least:
        thumb (PIL image), title (str)
    optional: subtitle (str), pages (int), angle (0/90/180/270),
              tooltip (str, shown when the mouse rests on the tile)

    Tiles can be dragged to a new place, removed with ✕, moved with ◀ ▶ and
    (if rotatable) rotated with ↺ ↻. on_change() is called after every change.
    """

    def __init__(self, master, placeholder, on_change=None, rotatable=True, stacked=False):
        super().__init__(
            master, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#C3D1E6", scrollbar_button_hover_color="#A9BBD6",
        )
        self.items = []
        self.columns = 0
        self.rotatable = rotatable
        self.stacked = stacked
        self.on_change = on_change or (lambda: None)

        self._parent_canvas.bind("<Configure>", lambda event: self.layout(), add="+")

        self.placeholder = ctk.CTkLabel(self, text=placeholder, font=font(14), text_color=MUTED, justify="left")
        self.placeholder.grid(row=0, column=0, padx=10, pady=60, sticky="w")

        self.marker = ctk.CTkFrame(self, width=5, height=PREVIEW_BOX, fg_color=GREEN, corner_radius=3)
        self._drag = None
        self.tooltip = Tooltip(self.winfo_toplevel())

    # ---------- adding / removing ----------

    def add(self, item):
        item.setdefault("angle", 0)
        item.setdefault("pages", 1)
        item.setdefault("subtitle", "")
        item.setdefault("tooltip", item["title"])
        self._create_tile(item)
        self.items.append(item)

    def remove(self, item):
        self.tooltip.hide()
        self.items.remove(item)
        item["frame"].destroy()
        self.refresh()

    def clear(self):
        for item in self.items:
            item["frame"].destroy()
        self.items = []
        self.refresh()

    # ---------- changing ----------

    def rotate(self, item, delta):
        item["angle"] = (item["angle"] + delta) % 360
        self.update_tile(item)
        self.on_change()

    def rotate_all(self, delta):
        for item in self.items:
            item["angle"] = (item["angle"] + delta) % 360
            self.update_tile(item)
        self.on_change()

    def move(self, item, step):
        self.move_to(item, self.items.index(item) + step)

    def move_to(self, item, new_index):
        new_index = max(0, min(len(self.items) - 1, new_index))
        if self.items.index(item) == new_index:
            return
        self.items.remove(item)
        self.items.insert(new_index, item)
        self.refresh()

    def reverse(self):
        self.items.reverse()
        self.refresh()

    def refresh(self):
        """Re-place all tiles in the current order and update the numbers."""
        if self.items:
            self.placeholder.grid_forget()
        else:
            self.placeholder.grid(row=0, column=0, padx=10, pady=60, sticky="w")
        for number, item in enumerate(self.items, start=1):
            item["number_label"].configure(text=str(number))
        self.columns = 0
        self.layout()
        self.on_change()

    def layout(self):
        if not self.items:
            return
        width = self._parent_canvas.winfo_width()
        columns = max(1, width // (TILE_WIDTH + 2 * TILE_PAD))
        if columns == self.columns:
            return
        self.columns = columns
        for index, item in enumerate(self.items):
            item["frame"].grid(row=index // columns, column=index % columns, padx=TILE_PAD, pady=TILE_PAD)

    # ---------- tiles ----------

    @staticmethod
    def _short(text, limit=20):
        return text if len(text) <= limit else text[:9] + "…" + text[-(limit - 10):]

    def _create_tile(self, item):
        tile = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=2,
                            border_color=BORDER, width=TILE_WIDTH)

        top = ctk.CTkFrame(tile, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 0))
        item["number_label"] = ctk.CTkLabel(top, text="", width=26, height=22, corner_radius=11,
                                            fg_color=NAVY, text_color="white", font=font(11, "bold"))
        item["number_label"].pack(side="left")
        ctk.CTkButton(top, text="✕", width=24, height=22, corner_radius=8, fg_color="transparent",
                      hover_color="#FDE2E2", text_color=MUTED, font=font(12),
                      command=lambda: self.remove(item)).pack(side="right")

        preview_area = ctk.CTkFrame(tile, fg_color=PREVIEW_BG, corner_radius=10,
                                    width=TILE_WIDTH - 16, height=PREVIEW_BOX + 12)
        preview_area.pack(padx=8, pady=4)
        preview_area.pack_propagate(False)
        image_label = ctk.CTkLabel(preview_area, text="", cursor="fleur")
        image_label.pack(expand=True)

        title_label = ctk.CTkLabel(tile, text="", font=font(11, "bold"), text_color=TEXT, height=16)
        title_label.pack(padx=8)
        info_label = ctk.CTkLabel(tile, text="", font=font(11), text_color=MUTED, height=14)
        info_label.pack(padx=8)

        controls = ctk.CTkFrame(tile, fg_color="transparent")
        controls.pack(fill="x", padx=8, pady=(4, 8))
        if self.rotatable:
            controls.columnconfigure((0, 1, 2, 3), weight=1)
            symbol_button(controls, "↺", lambda: self.rotate(item, -90)).grid(row=0, column=0, sticky="w")
            symbol_button(controls, "◀", lambda: self.move(item, -1), size=12, color=TEXT).grid(row=0, column=1)
            symbol_button(controls, "▶", lambda: self.move(item, 1), size=12, color=TEXT).grid(row=0, column=2)
            symbol_button(controls, "↻", lambda: self.rotate(item, 90)).grid(row=0, column=3, sticky="e")
        else:
            controls.columnconfigure((0, 1), weight=1)
            symbol_button(controls, "◀", lambda: self.move(item, -1), size=12, color=TEXT).grid(row=0, column=0, sticky="e", padx=4)
            symbol_button(controls, "▶", lambda: self.move(item, 1), size=12, color=TEXT).grid(row=0, column=1, sticky="w", padx=4)

        # Drag to re-order: grab the tile anywhere except on its buttons
        for widget in (tile, preview_area, image_label, title_label, info_label, top, controls):
            widget.bind("<ButtonPress-1>", lambda event: self._drag_start(event, item), add="+")
            widget.bind("<B1-Motion>", self._drag_motion, add="+")
            widget.bind("<ButtonRelease-1>", self._drag_end, add="+")

        for widget in (image_label, title_label, info_label):
            self.tooltip.attach(widget, lambda: item["tooltip"])

        item.update(frame=tile, image_label=image_label, title_label=title_label, info_label=info_label)
        self.update_tile(item)

    def update_tile(self, item):
        image = preview_image(item["thumb"], item["angle"], item["pages"], self.stacked)
        scale = PREVIEW_BOX / max(image.size)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        item["display"] = image
        item["ctk_image"] = ctk.CTkImage(light_image=image, size=size)
        item["image_label"].configure(image=item["ctk_image"])
        item["title_label"].configure(text=self._short(item["title"]))

        parts = []
        if item["subtitle"]:
            parts.append(item["subtitle"])
        if item["pages"] > 1:
            parts.append(plural(item["pages"], "page"))
        if item["angle"]:
            parts.append({90: "↻ 90°", 180: "180°", 270: "↺ 90°"}[item["angle"]])
        item["info_label"].configure(text="  ·  ".join(parts), text_color=GREEN if item["angle"] else MUTED)
        item["frame"].configure(border_color=GREEN if item["angle"] else BORDER)

    # ---------- drag & drop re-ordering ----------

    def _drag_start(self, event, item):
        self._drag = {"item": item, "x": event.x_root, "y": event.y_root, "active": False, "target": None}

    def _drag_motion(self, event):
        drag = self._drag
        if not drag:
            return
        if not drag["active"]:
            if abs(event.x_root - drag["x"]) + abs(event.y_root - drag["y"]) < 8:
                return
            drag["active"] = True
            self.tooltip.hide()
            self._make_ghost(drag["item"])
            drag["item"]["frame"].configure(fg_color=SUBCARD)

        drag["ghost"].geometry(f"+{event.x_root + 14}+{event.y_root + 10}")
        self._autoscroll(event.y_root)
        drag["target"] = self._target_index(event.x_root, event.y_root)
        self._show_marker(drag["target"])

    def _drag_end(self, event):
        drag, self._drag = self._drag, None
        if not drag or not drag["active"]:
            return
        drag["ghost"].destroy()
        self.marker.place_forget()
        item = drag["item"]
        item["frame"].configure(fg_color=CARD)

        target = drag["target"]
        if target is None:
            return
        old = self.items.index(item)
        if target > old:
            target -= 1
        self.move_to(item, target)

    def _make_ghost(self, item):
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-alpha", 0.85)
        ghost.attributes("-topmost", True)
        image = item["display"].copy()
        image.thumbnail((110, 110))
        photo = ImageTk.PhotoImage(image)
        label = tk.Label(ghost, image=photo, bd=2, relief="solid", bg=GREEN)
        label.image = photo
        label.pack()
        self._drag["ghost"] = ghost

    def _target_index(self, x_root, y_root):
        """Index where the dragged tile would be inserted (0 .. len(items))."""
        best, best_distance = None, None
        for index, item in enumerate(self.items):
            frame = item["frame"]
            cx = frame.winfo_rootx() + frame.winfo_width() / 2
            cy = frame.winfo_rooty() + frame.winfo_height() / 2
            # rows weigh more than columns, so the nearest tile is found in the right row
            distance = abs(cx - x_root) + 3 * abs(cy - y_root)
            if best_distance is None or distance < best_distance:
                best, best_distance = index, distance
        if best is None:
            return None
        frame = self.items[best]["frame"]
        after = x_root > frame.winfo_rootx() + frame.winfo_width() / 2
        return best + 1 if after else best

    def _show_marker(self, target):
        if target is None:
            self.marker.place_forget()
            return
        if target < len(self.items):
            frame = self.items[target]["frame"]
            x = frame.winfo_x() - TILE_PAD - 3
        else:
            frame = self.items[-1]["frame"]
            x = frame.winfo_x() + frame.winfo_width() + TILE_PAD - 3
        self.marker.configure(height=frame.winfo_height())
        self.marker.place(x=x, y=frame.winfo_y())
        self.marker.lift()

    def _autoscroll(self, y_root):
        canvas = self._parent_canvas
        top = canvas.winfo_rooty()
        bottom = top + canvas.winfo_height()
        if y_root < top + 40:
            canvas.yview_scroll(-1, "units")
        elif y_root > bottom - 40:
            canvas.yview_scroll(1, "units")
