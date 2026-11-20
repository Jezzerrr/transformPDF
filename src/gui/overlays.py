"""
Things that float over the app window:
- Toast: a short message (e.g. "PDF saved") that disappears by itself
- PageViewer: a large view of one page or image, with browsing, rotating and deleting
"""
import os
import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from src.gui.widgets import CARD, SUBCARD, GREEN, GREEN_HOVER, GREEN_LIGHT, TEXT, MUTED, RED, font, heading

AMBER = "#B7791F"
VIEWER_BG = "#1E2230"
VIEWER_PANEL = "#2A2F40"


# ==========================================================
# TOAST
# ==========================================================

class Toast:
    """
    A small card in the bottom-right corner, just above the save buttons.
    It closes by itself after a few seconds (a thin bar shows the time left),
    waits while the mouse is on it, and can be closed early with ✕.
    """

    def __init__(self, root):
        self.root = root
        self.frame = None
        self._job = None

    def show(self, title, message="", kind="success", file=None, folder=None, duration=6000):
        self.close()
        color = GREEN if kind == "success" else AMBER
        icon = "✔" if kind == "success" else "!"

        frame = ctk.CTkFrame(self.root, fg_color=CARD, corner_radius=14, border_width=2, border_color=color)
        self.frame = frame

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(12, 8))
        ctk.CTkLabel(body, text=icon, width=30, height=30, corner_radius=15, fg_color=color,
                     text_color="white", font=font(15, "bold")).pack(side="left", anchor="n", padx=(0, 12))

        text = ctk.CTkFrame(body, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(text, text=title, font=heading(15), text_color=TEXT, anchor="w").pack(anchor="w")
        if message:
            ctk.CTkLabel(text, text=message, font=font(12), text_color=MUTED, anchor="w", justify="left",
                         wraplength=330).pack(anchor="w")

        links = ctk.CTkFrame(text, fg_color="transparent")
        if file:
            self._link(links, "Open PDF", lambda: self._open(file))
        if folder:
            self._link(links, "Open folder", lambda: self._open(folder))
        if file or folder:
            links.pack(anchor="w", pady=(6, 0))

        ctk.CTkButton(body, text="✕", width=26, height=26, corner_radius=8, fg_color="transparent",
                      hover_color=SUBCARD, text_color=MUTED, font=font(13),
                      command=self.close).pack(side="left", anchor="n", padx=(10, 0))

        self.bar = ctk.CTkProgressBar(frame, height=4, corner_radius=2, fg_color=SUBCARD, progress_color=color)
        self.bar.set(1)
        self.bar.pack(fill="x", padx=14, pady=(0, 10))

        self.duration = self.remaining = duration
        self._last_tick = time.monotonic()
        self._slide(0)
        self._job = self.root.after(50, self._tick)

    def _link(self, parent, text, command):
        ctk.CTkButton(parent, text=text, command=command, width=10, height=26, corner_radius=8,
                      fg_color=GREEN_LIGHT, hover_color="#CDE8D7", text_color=GREEN_HOVER,
                      font=font(12, "bold")).pack(side="left", padx=(0, 6))

    def _open(self, path):
        try:
            os.startfile(Path(path))
        except OSError:
            pass
        self.close()

    def _slide(self, step, steps=8):
        """Slide up a little while appearing."""
        if self.frame is None:
            return
        offset = int(24 * (1 - step / steps) ** 2)
        self.frame.place(relx=1.0, rely=1.0, anchor="se", x=-44, y=-112 + offset)
        self.frame.lift()
        if step < steps:
            self.root.after(15, self._slide, step + 1)

    def _mouse_on_toast(self):
        x, y = self.root.winfo_pointerxy()
        f = self.frame
        return f.winfo_rootx() <= x < f.winfo_rootx() + f.winfo_width() and \
            f.winfo_rooty() <= y < f.winfo_rooty() + f.winfo_height()

    def _tick(self):
        if self.frame is None:
            return
        now = time.monotonic()
        elapsed, self._last_tick = (now - self._last_tick) * 1000, now
        if not self._mouse_on_toast():   # the time stands still while the mouse is on it
            self.remaining -= elapsed
            self.bar.set(max(0, self.remaining / self.duration))
        if self.remaining <= 0:
            self.close()
        else:
            self._job = self.root.after(50, self._tick)

    def close(self):
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None


# ==========================================================
# PAGE VIEWER
# ==========================================================

class PageViewer:
    """
    Large view over the whole working area (below the header).

        items      the live list of tiles (so deleting/rotating stays in sync)
        get_image  item -> big upright PIL image (rotation is applied here)
        describe   (item, position, count) -> (title, subtitle)
        rotate     (item, delta) -> None        delete  (item) -> None

    Keys: ← → browse, R rotate right, Delete delete, Esc close.
    Clicking the dark area next to the page closes the viewer too.
    """

    def __init__(self, root, top):
        self.root = root
        self.top = top
        self.overlay = None
        self._cache = {}
        self._bindings = []
        self._resize_job = None

    def is_open(self):
        return self.overlay is not None

    def open(self, items, item, get_image, describe, rotate, delete, delete_label="Delete"):
        self.close()
        self.items, self.get_image, self.describe = items, get_image, describe
        self.rotate_item, self.delete_item = rotate, delete
        self.index = items.index(item)

        # plain tk.Frame: CustomTkinter frames can't be placed with a height offset
        overlay = tk.Frame(self.root, bg=VIEWER_BG)
        self.overlay = overlay
        overlay.place(x=0, y=self.top, relwidth=1, relheight=1, height=-self.top)
        overlay.lift()

        # Top bar: what you're looking at + actions
        top = ctk.CTkFrame(overlay, fg_color=VIEWER_PANEL, corner_radius=0, height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        text = ctk.CTkFrame(top, fg_color="transparent")
        text.pack(side="left", padx=24)
        self.title_label = ctk.CTkLabel(text, text="", font=heading(18), text_color="white", anchor="w", height=24)
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(text, text="", font=font(12), text_color="#AAB2C5", anchor="w", height=16)
        self.subtitle_label.pack(anchor="w")

        ctk.CTkButton(top, text="✕  Close", width=90, height=34, corner_radius=10, fg_color="transparent",
                      hover_color="#3A4155", text_color="white", font=font(13, "bold"),
                      command=self.close).pack(side="right", padx=(6, 20))
        ctk.CTkButton(top, text=delete_label, width=90, height=34, corner_radius=10, fg_color="transparent",
                      border_width=1, border_color="#E5A3A3", hover_color="#4A2F36", text_color="#F3B4B4",
                      font=font(13, "bold"), command=self._delete).pack(side="right", padx=6)
        for symbol, delta in (("↻", 90), ("↺", -90)):
            ctk.CTkButton(top, text=symbol, width=40, height=34, corner_radius=10, fg_color="#3A4155",
                          hover_color="#4A5370", text_color="white", font=ctk.CTkFont(family="Segoe UI Symbol", size=18),
                          command=lambda d=delta: self._rotate(d)).pack(side="right", padx=3)

        # Bottom: position + keyboard hint
        bottom = ctk.CTkFrame(overlay, fg_color="transparent", height=40)
        bottom.pack(side="bottom", fill="x")
        self.counter_label = ctk.CTkLabel(bottom, text="", font=font(13, "bold"), text_color="white")
        self.counter_label.pack(side="left", padx=24)
        ctk.CTkLabel(bottom, text="←  →  browse     R  rotate     Delete  delete     Esc  close",
                     font=font(12), text_color="#7E879C").pack(side="right", padx=24)

        # Middle: arrows and the page
        middle = ctk.CTkFrame(overlay, fg_color="transparent")
        middle.pack(fill="both", expand=True)
        self.prev_button = self._arrow(middle, "‹", -1)
        self.prev_button.pack(side="left", padx=20)
        self.next_button = self._arrow(middle, "›", 1)
        self.next_button.pack(side="right", padx=20)
        self.stage = ctk.CTkFrame(middle, fg_color="transparent")
        self.stage.pack(fill="both", expand=True, pady=12)
        self.image_label = ctk.CTkLabel(self.stage, text="")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.stage.bind("<Button-1>", lambda event: self.close())
        self.stage.bind("<Configure>", self._on_resize, add="+")

        for sequence, handler in (("<Left>", lambda e: self._step(-1)), ("<Right>", lambda e: self._step(1)),
                                  ("<Escape>", lambda e: self.close()), ("<Delete>", lambda e: self._delete()),
                                  ("<r>", lambda e: self._rotate(90)), ("<R>", lambda e: self._rotate(90))):
            self._bindings.append((sequence, self.root.bind(sequence, handler, add="+")))
        overlay.focus_set()

        self.root.update_idletasks()
        self.show()

    def _arrow(self, parent, text, step):
        return ctk.CTkButton(parent, text=text, width=52, height=90, corner_radius=14, fg_color=VIEWER_PANEL,
                             hover_color="#3A4155", text_color="white", font=font(34),
                             command=lambda: self._step(step))

    def show(self):
        if not self.overlay:
            return
        if not self.items:
            self.close()
            return
        self.index = max(0, min(self.index, len(self.items) - 1))
        item = self.items[self.index]

        key = id(item["run"]) if "run" in item else id(item["thumb"])
        if key not in self._cache:
            self.root.configure(cursor="watch")
            self.root.update_idletasks()
            try:
                self._cache[key] = self.get_image(item)
            finally:
                self.root.configure(cursor="")
        image = self._cache[key]
        if item.get("angle"):
            image = image.rotate(-item["angle"], expand=True)

        width = max(100, self.stage.winfo_width() - 24)
        height = max(100, self.stage.winfo_height() - 24)
        scaling = ctk.ScalingTracker.get_widget_scaling(self.stage)
        scale = min(width / scaling / image.width, height / scaling / image.height)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        self._ctk_image = ctk.CTkImage(light_image=image, size=size)
        self.image_label.configure(image=self._ctk_image)

        title, subtitle = self.describe(item, self.index + 1, len(self.items))
        self.title_label.configure(text=title)
        self.subtitle_label.configure(text=subtitle)
        self.counter_label.configure(text=f"{self.index + 1} / {len(self.items)}")
        self.prev_button.configure(state="normal" if self.index > 0 else "disabled")
        self.next_button.configure(state="normal" if self.index < len(self.items) - 1 else "disabled")

    def _on_resize(self, event):
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self.show)

    def _step(self, step):
        new = self.index + step
        if 0 <= new < len(self.items):
            self.index = new
            self.show()

    def _rotate(self, delta):
        if self.items:
            self.rotate_item(self.items[self.index], delta)
            self.show()

    def _delete(self):
        if self.items:
            self.delete_item(self.items[self.index])
            self.show()   # shows the next one (or closes when nothing is left)

    def close(self):
        if self.overlay is None:
            return
        for sequence, func_id in self._bindings:
            self.root.unbind(sequence, func_id)
        self._bindings = []
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
            self._resize_job = None
        self.overlay.destroy()
        self.overlay = None
        self._cache = {}
