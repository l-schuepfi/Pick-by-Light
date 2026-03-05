"""

    Pick-by-Light System
    --------------------------------------------------------------
    Class for tkinter GUI interface, which automatically maximizes
    a displayed traffic light on a canvas within a frame.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import tkinter as tk

from colors import color_palette


class AutoScalingTrafficLightCanvas(tk.Canvas):
    def __init__(self, master: tk.Frame, **kwargs):
        super().__init__(master, **kwargs)
        self.state: str = "green"
        self.master.bind("<Configure>", self._rescale, add="+")

    def draw_traffic_light(self, state: str) -> None:
        """
        Draws a traffic light on the frame ‘traffic_lights’.
        state: 'red', 'yellow' or 'green'
        """
        self.state = state

        w: int = self.master.winfo_width()
        h: int = self.master.winfo_height()

        if w <= 0 or h <= 0:
            return

        self.config(width=w, height=h)
        self.delete("all")

        # Colors
        colors: dict[str, str] = {
            "red": color_palette["traffic_light_off"],
            "yellow": color_palette["traffic_light_off"],
            "green": color_palette["traffic_light_off"],
        }

        if state in colors:
            if state == "red":
                colors["red"] = "red"
            elif state == "yellow":
                colors["yellow"] = "yellow"
            elif state == "green":
                colors["green"] = "green"

        # Geometry
        radius: float = min(w, h) * 0.15
        center_x: float = w / 2
        spacing: float = radius * 2.2
        start_y: float = h / 2 - spacing

        # Red
        self.create_oval(
            center_x - radius,
            start_y - radius,
            center_x + radius,
            start_y + radius,
            fill=colors["red"],
            outline="",
        )

        # Yellow
        self.create_oval(
            center_x - radius,
            start_y + spacing - radius,
            center_x + radius,
            start_y + spacing + radius,
            fill=colors["yellow"],
            outline="",
        )

        # Green
        self.create_oval(
            center_x - radius,
            start_y + 2 * spacing - radius,
            center_x + radius,
            start_y + 2 * spacing + radius,
            fill=colors["green"],
            outline="",
        )

    def _rescale(self, event) -> None:
        self.draw_traffic_light(self.state)
