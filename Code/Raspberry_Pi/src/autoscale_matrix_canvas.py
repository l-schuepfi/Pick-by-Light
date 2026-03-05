"""

    Pick-by-Light System
    --------------------------------------------------------
    Class for tkinter GUI interface, which automatically
    maximizes a displayed matrix on a canvas within a frame.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import tkinter as tk

from colors import color_palette


class AutoScalingMatrixCanvas(tk.Canvas):
    def __init__(self, master: tk.Frame, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.active_col: int = 0
        self.active_row: int = 0
        self.amount_rows: int = 0
        self.amount_cols: int = 0
        self.table_rects: list[list[int]] = []
        self.master.bind("<Configure>", self._rescale, add="+")

    def draw_table(
        self, active_row: int, active_col: int, amount_rows: int, amount_cols: int
    ) -> None:
        self.active_col = active_col
        self.active_row = active_row
        self.amount_rows = amount_rows
        self.amount_cols = amount_cols

        max_w: int = self.master.winfo_width()
        max_h: int = self.master.winfo_height()

        if max_w <= 0 or max_h <= 0:
            return

        self.config(width=max_w, height=max_h)
        self.delete("all")

        pad: int = 2
        square_size: float = min(
            0.95 * (max_w - (amount_cols + 1) * pad) / amount_cols,
            0.95 * (max_h - (amount_rows + 1) * pad) / amount_rows,
        )

        self.table_rects.clear()
        for r in range(amount_rows):
            row_rects: list[int] = []
            for c in range(amount_cols):
                x1: float = (
                    max_w / 2
                    - (square_size + pad) * (amount_cols - 1) / 2
                    + (square_size + pad) * c
                    - square_size / 2
                )
                x2: float = x1 + square_size
                y1: float = (
                    max_h / 2
                    - (square_size + pad) * (amount_rows - 1) / 2
                    + (square_size + pad) * r
                    - square_size / 2
                )
                y2: float = y1 + square_size
                rect: int = self.create_rectangle(
                    x1, y1, x2, y2, fill=color_palette["active_rect"], outline="white", width=1
                )
                row_rects.append(rect)
            self.table_rects.append(row_rects)

    def set_active_rect_color(self, color: str = "green") -> None:
        rect: int = self.table_rects[self.active_row][self.active_col]
        self.itemconfig(rect, fill=color)

    def _rescale(self, event) -> None:
        self.draw_table(self.active_row, self.active_col, self.amount_rows, self.amount_cols)
