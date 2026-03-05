"""

    Pick-by-Light System
    ----------------------------------------------------
    Class for tkinter GUI interface, which automatically
    maximizes a displayed text within a frame.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import tkinter as tk
import tkinter.font as tkFont


class AutoScalingTextLabel(tk.Label):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.font: tkFont.Font = tkFont.Font(family="Arial")
        self.max_w: int | None = None
        self.max_h: int | None = None
        self.master.bind("<Configure>", self._store_size_and_rescale, add="+")

    def compute_best_font_size(self, text: str) -> int:
        if (
            self.max_w is None
            or self.max_w <= 1
            or self.max_h is None
            or self.max_h <= 1
            or not text
        ):
            return 10

        low: int = 1
        high: int = 300
        best_size: int = 1
        mid: int = 0
        w: int = 0
        h: int = 0

        while low <= high:
            mid = (low + high) // 2
            self.font.configure(size=mid)

            w = self.font.measure(text)
            h = self.font.metrics("linespace")

            if w <= self.max_w and h <= self.max_h:
                best_size = mid
                low = mid + 1
            else:
                high = mid - 1

        return best_size

    def change_text(self, new_text: str) -> None:
        self.config(text=new_text)
        if self.max_w and self.max_h:
            self._rescale()

    def _rescale(self) -> None:
        size: int = self.compute_best_font_size(self.cget("text"))
        self.config(font=("Arial", size))

    def _store_size_and_rescale(self, event) -> None:
        self.max_w = self.master.winfo_width()
        self.max_h = self.master.winfo_height()
        self._rescale()
