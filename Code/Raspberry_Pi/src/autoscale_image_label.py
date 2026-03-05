"""

    Pick-by-Light System
    ----------------------------------------------------
    Class for tkinter GUI interface, which automatically
    maximizes displayed images within a frame.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import os
import tkinter as tk

from PIL import Image, ImageTk  # type: ignore[attr-defined]


class AutoScalingImageLabel(tk.Label):
    def __init__(self, master: tk.Frame, image_path: str | None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.orig_img: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.max_w: int | None = None
        self.max_h: int | None = None
        self.load_image(image_path)
        self.master.bind("<Configure>", self._store_size_and_rescale, add="+")

    def load_image(self, image_path: str | None) -> None:
        if image_path is not None and os.path.exists(image_path):
            self.orig_img = Image.open(image_path)
        else:
            self.orig_img = None
        if self.max_w and self.max_h:
            self._rescale()

    def _rescale(self) -> None:
        if self.orig_img is None:
            return

        if self.max_w is None or self.max_w < 10 or self.max_h is None or self.max_h < 10:
            return

        orig_w: int = 0
        orig_h: int = 0
        orig_w, orig_h = self.orig_img.size
        ratio: float = min(self.max_w / orig_w, self.max_h / orig_h)

        new_w: int = int(orig_w * ratio)
        new_h: int = int(orig_h * ratio)

        resized_img: Image.Image = self.orig_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized_img)

        self.config(image=self.photo)

    def _store_size_and_rescale(self, event) -> None:
        self.max_w = self.master.winfo_width()
        self.max_h = self.master.winfo_height()
        self._rescale()
