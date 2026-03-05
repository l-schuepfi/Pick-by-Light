"""

    Pick-by-Light System
    ----------------------------------------------------------------------------
    Class to show the actual items on the monitor. Reaction to sensor changes
    is possible through queues. 'to_gui_queue' is used to react to sensor values
    from outside. This allows automatic forwarding to the next item or error
    messages to be displayed. 'from_gui_queue' can be used to communicate the
    forwarding and other changes to the sensor loop.

    It uses tkinter for building the grafical interface and uses the principle
    of frames to split the content. All texts and images are automatically set
    to the maximum size using own helper classes.

    After calibration and RFID readout are done, it displays the item with its
    name, image, position and amount of remaining parts from the excel database.

    It calls updates from the sensor loop every 100ms.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import os
import queue

# import subprocess
import tkinter as tk

# import pygame
from multiprocessing.queues import Queue as mpQueue
from multiprocessing.synchronize import Event as mpEvent

from autoscale_image_label import AutoScalingImageLabel
from autoscale_matrix_canvas import AutoScalingMatrixCanvas
from autoscale_text_label import AutoScalingTextLabel
from autoscale_traffic_light_canvas import AutoScalingTrafficLightCanvas
from colors import color_palette

# Treiber-Umgebung für Tonausgabe setzen
# os.environ['SDL_AUDIODRIVER'] = 'alsa'
# pygame.init()
# pygame.mixer.pre_init(44100, -16, 2, 512) # Puffer optimieren
# pygame.mixer.init()

# --- Variables ---
BLINK_INTERVAL = 500  # ms


class PartViewer:
    def __init__(
        self,
        root: tk.Tk,
        to_gui_queue: mpQueue,
        from_gui_queue: mpQueue,
        database: dict[str, dict[str, list[list[dict[str, float | str]]]]],
        dictionary: dict[str, str],
        stop_event: mpEvent,
        load_cell_usage: bool,
    ) -> None:
        self.root: tk.Tk = root
        self.to_gui_queue: mpQueue = to_gui_queue
        self.from_gui_queue: mpQueue = from_gui_queue
        self.database: dict[str, dict[str, list[list[dict[str, float | str]]]]] = database
        self.dictionary: dict[str, str] = dictionary
        self.stop_event: mpEvent = stop_event
        self.load_cell_usage: bool = load_cell_usage

        self.root.title(self.dictionary["title"])

        self.current_picked_amount: int = 0
        # self.error_sound: pygame.mixer.Sound = pygame.mixer.Sound("data/error_sound.mp3")

        self.vehicle_name: str | None = None
        self.calibration_load_cell_active: bool = False
        self.starting_calibrations_completed: bool = False
        self.error_active: bool = False
        self.items: list[dict[str, float | str]] | None = None

        self.index: int = 0
        self.blink_job: str | None = None
        self.blink_state: bool = False

        # UI-Container
        self.init_fragments()

        self.heading_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.heading_text,
            text=self.dictionary["heading"],
            bg="white",
            bd=0,
            highlightthickness=0,
            font=("Arial", 72),
        )
        self.heading_label.place(relx=0.5, rely=0.4, anchor="center")

        self.heading_label_with_image: AutoScalingImageLabel = AutoScalingImageLabel(
            self.heading_image, image_path=None, bg="white", bd=0, highlightthickness=0
        )
        self.heading_label_with_image.place(relx=0.5, rely=0.5, anchor="center")
        if self.vehicle_name:
            self.heading_label_with_image.load_image(f"img/Vehicles/{self.vehicle_name}.jpg")

        self.calibration_hint_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.calibration_hint,
            text=self.dictionary["calibration_hint"],
            bg="white",
            bd=0,
            highlightthickness=0,
            font=("Arial", 128),
        )
        self.calibration_hint_label.place(relx=0.5, rely=0.5, anchor="center")

        self.content_hint: AutoScalingTextLabel = AutoScalingTextLabel(
            self.content,
            text=self.dictionary["content_rfid_hint"],
            bg="white",
            bd=0,
            highlightthickness=0,
            font=("Arial", 48),
        )
        self.content_hint.place(relx=0.5, rely=0.5, anchor="center")

        self.img_label: AutoScalingImageLabel = AutoScalingImageLabel(
            self.left_top, image_path=None, bg="white", bd=0, highlightthickness=0
        )
        self.left_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.left_bottom_top_left,
            text="",
            bg="white",
            bd=0,
            highlightthickness=0,
            font=("Arial", 48),
        )
        self.sketch_goods_receiving_warehouse: AutoScalingImageLabel = AutoScalingImageLabel(
            self.left_bottom_top_mid,
            image_path="img/Wareneingangslager_Skizze.jpg",
            bg="white",
            bd=0,
            highlightthickness=0,
        )
        self.right_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.left_bottom_top_right,
            text="",
            bg="white",
            bd=0,
            highlightthickness=0,
            font=("Arial", 48),
        )
        self.table_canvas: AutoScalingMatrixCanvas = AutoScalingMatrixCanvas(
            self.table_frame, highlightthickness=0, bd=0, bg="white"
        )

        self.name_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.right_top, bg="white", bd=0, highlightthickness=0, font=("Arial", 32)
        )
        self.id_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.right_mid, bg="white", bd=0, highlightthickness=0, font=("Arial", 32)
        )
        self.remaining_amount_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.right_bottom_left,
            bg=color_palette["light_green"],
            bd=0,
            highlightthickness=0,
            font=("Arial", 220),
        )
        self.complete_amount_label: AutoScalingTextLabel = AutoScalingTextLabel(
            self.right_bottom_rigth,
            bg=color_palette["light_green"],
            bd=0,
            highlightthickness=0,
            font=("Arial", 220),
        )

        self.traffic_canvas: AutoScalingTrafficLightCanvas = AutoScalingTrafficLightCanvas(
            self.traffic_lights, bg="white", highlightthickness=0, bd=0
        )

        self.status_text: AutoScalingTextLabel = AutoScalingTextLabel(
            self.status_description,
            bg="white",
            fg="green",
            bd=0,
            highlightthickness=0,
            font=("Arial", 48),
        )

        self.show_calibration_hint()

    def show_calibration_hint(self) -> None:
        detail_widgets: list[
            AutoScalingTextLabel
            | AutoScalingImageLabel
            | AutoScalingMatrixCanvas
            | AutoScalingTrafficLightCanvas
        ] = [
            self.content_hint,
            self.img_label,
            self.left_label,
            self.sketch_goods_receiving_warehouse,
            self.right_label,
            self.name_label,
            self.id_label,
            self.remaining_amount_label,
            self.complete_amount_label,
            self.table_canvas,
            self.traffic_canvas,
            self.status_text,
        ]

        for widget in detail_widgets:
            widget.place_forget()

        detail_frames: list[tk.Frame] = [
            self.content,
            self.display_sep2,
            self.status_bar,
            self.left,
            self.sep_vert,
            self.right,
            self.left_top,
            self.left_sep,
            self.left_bottom,
            self.left_bottom_top,
            self.left_bottom_sep,
            self.left_bottom_bottom,
            self.left_bottom_top_left,
            self.left_bottom_top_sep1,
            self.left_bottom_top_mid,
            self.left_bottom_top_sep2,
            self.left_bottom_top_right,
            self.table_frame,
            self.right_top,
            self.right_sep1,
            self.right_mid,
            self.right_sep2,
            self.right_bottom,
            self.right_bottom_left,
            self.right_bottom_rigth,
            self.traffic_lights,
            self.status_sep,
            self.status_description,
        ]

        for frame in detail_frames:
            frame.place_forget()

        self.calibration_hint_label.change_text(self.dictionary["calibration_hint"])
        self.calibration_hint_label.place(relx=0.5, rely=0.5, anchor="center")

    def show_content_hint(self) -> None:
        detail_widgets: list[
            AutoScalingTextLabel
            | AutoScalingImageLabel
            | AutoScalingMatrixCanvas
            | AutoScalingTrafficLightCanvas
        ] = [
            self.calibration_hint_label,
            self.img_label,
            self.left_label,
            self.sketch_goods_receiving_warehouse,
            self.right_label,
            self.name_label,
            self.id_label,
            self.remaining_amount_label,
            self.complete_amount_label,
        ]

        for widget in detail_widgets:
            widget.place_forget()

        detail_frames: list[tk.Frame] = [
            self.calibration_hint,
            self.left,
            self.sep_vert,
            self.right,
            self.left_top,
            self.left_sep,
            self.left_bottom,
            self.left_bottom_top,
            self.left_bottom_sep,
            self.left_bottom_bottom,
            self.left_bottom_top_left,
            self.left_bottom_top_sep1,
            self.left_bottom_top_mid,
            self.left_bottom_top_sep2,
            self.left_bottom_top_right,
            self.right_top,
            self.right_sep1,
            self.right_mid,
            self.right_sep2,
            self.right_bottom,
            self.right_bottom_left,
            self.right_bottom_rigth,
        ]

        for frame in detail_frames:
            frame.place_forget()

        rel_sep: float = 0.01
        full_size: float = 1.0
        origin: float = 0.0
        rel_sep /= full_size - 2 * rel_sep
        self.content.place(
            relx=origin, rely=0.15 + rel_sep / 2.0, relwidth=full_size, relheight=0.7 - rel_sep
        )
        self.display_sep2.place(
            relx=origin, rely=0.85 - rel_sep / 2.0, relwidth=full_size, relheight=rel_sep
        )
        self.status_bar.place(
            relx=origin,
            rely=0.85 + rel_sep / 2.0,
            relwidth=full_size,
            relheight=0.15 - rel_sep / 2.0,
        )
        self.place_status_bar_frames()

        self.content_hint.place(relx=0.5, rely=0.5, anchor="center")
        self.traffic_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.status_text.place(relx=0.5, rely=0.5, anchor="center")

    def show_main_content(self) -> None:
        self.content_hint.place_forget()
        self.calibration_hint_label.place_forget()

        self.place_content_frames()
        self.place_status_bar_frames()

        if self.vehicle_name:
            self.heading_label_with_image.load_image(f"img/Vehicles/{self.vehicle_name}.jpg")

        self.img_label.place(relx=0.5, rely=0.5, anchor="center")
        self.left_label.place(relx=0.5, rely=0.5, anchor="center")
        self.sketch_goods_receiving_warehouse.place(relx=0.5, rely=0.5, anchor="center")
        self.right_label.place(relx=0.5, rely=0.5, anchor="center")
        self.table_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.name_label.place(relx=0.5, rely=0.5, anchor="center")
        self.id_label.place(relx=0.5, rely=0.5, anchor="center")
        self.remaining_amount_label.place(relx=0.5, rely=0.5, anchor="center")
        self.complete_amount_label.place(relx=0.5, rely=0.5, anchor="center")
        self.table_frame.place(relx=0.5, rely=0.5, relwidth=1, relheight=1, anchor="center")
        self.traffic_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Display first element
        if self.items is not None:
            self.show_item(self.items[self.index])

    # def play_error_sound_as_user(self) -> None:
    #     # system should run 'aplay' as User 'admin'
    #     # 'plughw:1,0' is our jack (Card 1)
    #     cmd: str = "sudo -u admin aplay -D plughw:1,0 data/error_sound.wav"
    #     subprocess.Popen(cmd, shell=True)

    def place_content_frames(self) -> None:
        rel_sep: float = 0.01
        full_size: float = 1.0
        origin: float = 0.0
        rel_sep /= full_size - 2 * rel_sep

        self.content.place(
            relx=origin, rely=0.15 + rel_sep / 2.0, relwidth=full_size, relheight=0.7 - rel_sep
        )

        self.display_sep2.place(
            relx=origin, rely=0.85 - rel_sep / 2.0, relwidth=full_size, relheight=rel_sep
        )

        self.status_bar.place(
            relx=origin,
            rely=0.85 + rel_sep / 2.0,
            relwidth=full_size,
            relheight=0.15 - rel_sep / 2.0,
        )

        self.left.place(relx=origin, rely=origin, relwidth=0.5 - rel_sep / 2.0, relheight=full_size)
        self.sep_vert.place(
            relx=0.5 - rel_sep / 2.0, rely=origin, relwidth=rel_sep, relheight=full_size
        )
        self.right.place(
            relx=0.5 + rel_sep / 2.0, rely=origin, relwidth=0.5 - rel_sep / 2.0, relheight=full_size
        )

        # in the left area: top / separator / bottom (3 fragments)
        rel_sep_x: float = rel_sep / (0.5 - rel_sep / 2.0)
        rel_sep_y: float = rel_sep / (0.85 - rel_sep / 2.0)
        self.left_top.place(
            relx=origin, rely=origin, relwidth=full_size, relheight=0.45 - rel_sep_y / 2.0
        )
        self.left_sep.place(
            relx=origin, rely=0.45 - rel_sep_y / 2.0, relwidth=full_size, relheight=rel_sep_y
        )
        self.left_bottom.place(
            relx=origin,
            rely=0.45 + rel_sep_y / 2.0,
            relwidth=full_size,
            relheight=0.55 - rel_sep_y / 2.0,
        )

        # in the lower left area: top / separator / bottom (3 fragments)
        rel_sep_y_bottomleft: float = rel_sep_y / (0.55 - rel_sep_y / 2.0)
        self.left_bottom_top.place(
            relx=origin, rely=origin, relwidth=full_size, relheight=0.3 - rel_sep_y_bottomleft / 2.0
        )
        self.left_bottom_sep.place(
            relx=origin,
            rely=0.3 - rel_sep_y_bottomleft / 2.0,
            relwidth=full_size,
            relheight=rel_sep_y_bottomleft,
        )
        self.left_bottom_bottom.place(
            relx=origin,
            rely=0.3 + rel_sep_y_bottomleft / 2.0,
            relwidth=full_size,
            relheight=0.7 - rel_sep_y_bottomleft / 2.0,
        )

        # in the lower left upper area: left / separator / center / separator / right (5 fragments)
        self.left_bottom_top_left.place(
            relx=origin, rely=origin, relwidth=0.4 - rel_sep_x * 2.0 / 3.0, relheight=full_size
        )
        self.left_bottom_top_sep1.place(
            relx=0.4 - rel_sep_x * 2.0 / 3.0, rely=origin, relwidth=rel_sep_x, relheight=full_size
        )
        self.left_bottom_top_mid.place(
            relx=0.4 + rel_sep_x / 3.0,
            rely=origin,
            relwidth=0.2 - rel_sep_x * 2.0 / 3.0,
            relheight=full_size,
        )
        self.left_bottom_top_sep2.place(
            relx=0.6 - rel_sep_x / 3.0, rely=origin, relwidth=rel_sep_x, relheight=full_size
        )
        self.left_bottom_top_right.place(
            relx=0.6 + rel_sep_x * 2.0 / 3.0,
            rely=origin,
            relwidth=0.4 - rel_sep_x * 2.0 / 3.0,
            relheight=full_size,
        )

        # on the right side: top / separator / middle / separator / bottom (5 fragments)
        self.right_top.place(
            relx=origin, rely=origin, relwidth=full_size, relheight=0.15 - rel_sep_y * 2.0 / 3.0
        )
        self.right_sep1.place(
            relx=origin, rely=0.15 - rel_sep_y * 2.0 / 3.0, relwidth=full_size, relheight=rel_sep_y
        )
        self.right_mid.place(
            relx=origin,
            rely=0.15 + rel_sep_y / 3.0,
            relwidth=full_size,
            relheight=0.1 - rel_sep_y * 2.0 / 3.0,
        )
        self.right_sep2.place(
            relx=origin, rely=0.25 - rel_sep_y / 3.0, relwidth=full_size, relheight=rel_sep_y
        )
        self.right_bottom.place(
            relx=origin,
            rely=0.25 + rel_sep_y * 2.0 / 3.0,
            relwidth=full_size,
            relheight=0.75 - rel_sep_y * 2.0 / 3.0,
        )

        # split the lower right area
        self.right_bottom_left.place(relx=origin, rely=origin, relwidth=0.6, relheight=1.0)
        self.right_bottom_rigth.place(relx=0.6, rely=origin, relwidth=0.4, relheight=1.0)

    def place_status_bar_frames(self) -> None:
        rel_sep: float = 0.01
        full_size: float = 1.0
        origin: float = 0.0
        rel_sep /= full_size - 2 * rel_sep

        self.traffic_lights.place(
            relx=origin, rely=origin, relwidth=0.15 - rel_sep / 2.0, relheight=1.0
        )
        self.status_sep.place(
            relx=0.15 - rel_sep / 2.0, rely=origin, relwidth=rel_sep, relheight=1.0
        )
        self.status_description.place(
            relx=0.15 + rel_sep / 2.0, rely=origin, relwidth=0.85 - rel_sep / 2.0, relheight=1.0
        )

    def init_fragments(self) -> None:
        # Edge (left & right)
        rel_sep: float = 0.01
        full_size: float = 1.0
        origin: float = 0.0
        self.outer_left: tk.Frame = tk.Frame(
            self.root, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.outer_left.place(relx=origin, rely=origin, relwidth=rel_sep, relheight=full_size)

        self.inner_root: tk.Frame = tk.Frame(self.root, bg="white", bd=0, highlightthickness=0)
        self.inner_root.place(
            relx=rel_sep, rely=origin, relwidth=full_size - 2 * rel_sep, relheight=full_size
        )

        self.outer_right: tk.Frame = tk.Frame(
            self.root, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.outer_right.place(
            relx=full_size - rel_sep, rely=origin, relwidth=rel_sep, relheight=full_size
        )

        # Border (top & bottom)
        self.outer_top: tk.Frame = tk.Frame(
            self.inner_root, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.outer_top.place(relx=origin, rely=origin, relwidth=full_size, relheight=rel_sep)

        self.display_space: tk.Frame = tk.Frame(
            self.inner_root, bg="white", bd=0, highlightthickness=0
        )
        self.display_space.place(
            relx=origin, rely=rel_sep, relwidth=full_size, relheight=full_size - 2 * rel_sep
        )

        self.outer_bottom: tk.Frame = tk.Frame(
            self.inner_root, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.outer_bottom.place(
            relx=origin, rely=full_size - rel_sep, relwidth=full_size, relheight=rel_sep
        )

        # Top: Heading (project name), center: main display area, bottom: status bar
        rel_sep /= full_size - 2 * rel_sep
        self.heading: tk.Frame = tk.Frame(
            self.display_space, bg="white", bd=0, highlightthickness=0
        )
        self.heading.place(
            relx=origin, rely=origin, relwidth=full_size, relheight=0.15 - rel_sep / 2.0
        )

        self.display_sep: tk.Frame = tk.Frame(
            self.display_space, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.display_sep.place(
            relx=origin, rely=0.15 - rel_sep / 2.0, relwidth=full_size, relheight=rel_sep
        )

        self.calibration_hint: tk.Frame = tk.Frame(
            self.display_space, bg="white", bd=0, highlightthickness=0
        )
        self.calibration_hint.place(
            relx=origin,
            rely=0.15 + rel_sep / 2.0,
            relwidth=full_size,
            relheight=0.85 - rel_sep / 2.0,
        )

        self.content: tk.Frame = tk.Frame(
            self.display_space, bg="white", bd=0, highlightthickness=0
        )
        self.content.place(
            relx=origin, rely=0.15 + rel_sep / 2.0, relwidth=full_size, relheight=0.7 - rel_sep
        )

        self.display_sep2: tk.Frame = tk.Frame(
            self.display_space, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.display_sep2.place(
            relx=origin, rely=0.85 - rel_sep / 2.0, relwidth=full_size, relheight=rel_sep
        )

        self.status_bar: tk.Frame = tk.Frame(
            self.display_space, bg="white", bd=0, highlightthickness=0
        )
        self.status_bar.place(
            relx=origin,
            rely=0.85 + rel_sep / 2.0,
            relwidth=full_size,
            relheight=0.15 - rel_sep / 2.0,
        )

        # now within heading: left / separator / right
        self.heading_text: tk.Frame = tk.Frame(self.heading, bg="white", bd=0, highlightthickness=0)
        self.heading_text.place(
            relx=origin, rely=rel_sep, relwidth=0.85 - rel_sep / 2.0, relheight=1.0
        )

        self.heading_sep: tk.Frame = tk.Frame(
            self.heading, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.heading_sep.place(
            relx=0.85 - rel_sep / 2.0, rely=origin, relwidth=rel_sep, relheight=1.0
        )

        self.heading_image: tk.Frame = tk.Frame(
            self.heading, bg="white", bd=0, highlightthickness=0
        )
        self.heading_image.place(
            relx=0.85 + rel_sep / 2.0, rely=origin, relwidth=0.15 - rel_sep / 2.0, relheight=1.0
        )

        self.left: tk.Frame = tk.Frame(self.content, bg="white", bd=0, highlightthickness=0)
        self.sep_vert: tk.Frame = tk.Frame(
            self.content, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.right: tk.Frame = tk.Frame(self.content, bg="white", bd=0, highlightthickness=0)
        self.left_top: tk.Frame = tk.Frame(self.left, bg="white", bd=0, highlightthickness=0)
        self.left_sep: tk.Frame = tk.Frame(
            self.left, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.left_bottom: tk.Frame = tk.Frame(self.left, bg="white", bd=0, highlightthickness=0)
        self.left_bottom_top: tk.Frame = tk.Frame(
            self.left_bottom, bg="white", bd=0, highlightthickness=0
        )
        self.left_bottom_sep: tk.Frame = tk.Frame(
            self.left_bottom, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.left_bottom_bottom: tk.Frame = tk.Frame(
            self.left_bottom, bg="white", bd=0, highlightthickness=0
        )
        self.left_bottom_top_left: tk.Frame = tk.Frame(
            self.left_bottom_top, bg="white", bd=0, highlightthickness=0
        )
        self.left_bottom_top_sep1: tk.Frame = tk.Frame(
            self.left_bottom_top, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.left_bottom_top_mid: tk.Frame = tk.Frame(
            self.left_bottom_top, bg="white", bd=0, highlightthickness=0
        )
        self.left_bottom_top_sep2: tk.Frame = tk.Frame(
            self.left_bottom_top, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.left_bottom_top_right: tk.Frame = tk.Frame(
            self.left_bottom_top, bg="white", bd=0, highlightthickness=0
        )
        self.table_frame: tk.Frame = tk.Frame(self.left_bottom_bottom, bd=0, highlightthickness=0)
        self.right_top: tk.Frame = tk.Frame(self.right, bg="white", bd=0, highlightthickness=0)
        self.right_sep1: tk.Frame = tk.Frame(
            self.right, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.right_mid: tk.Frame = tk.Frame(self.right, bg="white", bd=0, highlightthickness=0)
        self.right_sep2: tk.Frame = tk.Frame(
            self.right, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.right_bottom: tk.Frame = tk.Frame(
            self.right, bg=color_palette["light_green"], bd=0, highlightthickness=0
        )
        self.right_bottom_left: tk.Frame = tk.Frame(
            self.right_bottom, bg=color_palette["light_green"], bd=0, highlightthickness=0
        )
        self.right_bottom_rigth: tk.Frame = tk.Frame(
            self.right_bottom, bg=color_palette["light_green"], bd=0, highlightthickness=0
        )

        # now within status_bar: left / separator / right
        self.traffic_lights: tk.Frame = tk.Frame(
            self.status_bar, bg="white", bd=0, highlightthickness=0
        )
        self.status_sep: tk.Frame = tk.Frame(
            self.status_bar, bg=color_palette["border"], bd=0, highlightthickness=0
        )
        self.status_description: tk.Frame = tk.Frame(
            self.status_bar, bg="white", bd=0, highlightthickness=0
        )

    def flatten_data(
        self, data: dict[str, list[list[dict[str, float | str]]]]
    ) -> list[dict[str, float | str]]:
        flat = []
        for orientation, rows in data.items():
            for row_idx, row in enumerate(rows):
                for col_idx, item in enumerate(row):
                    if item["amount"] != 0:
                        flat.append(
                            {
                                "name": item["name"],
                                "id": item["id"],
                                "weight": item["weight"],
                                "amount": item["amount"],
                                "orientation": orientation,
                                "row_idx": row_idx,
                                "col_idx": col_idx,
                                "row_amount": len(rows),
                                "col_amount": len(row),
                            }
                        )
        return flat

    def blink(self) -> None:
        self.blink_state = not self.blink_state

        if self.blink_state:
            self.table_canvas.set_active_rect_color("green")
            if self.left_label.cget("text") != "":
                self.left_label.config(bg=color_palette["light_green"])
                self.left_bottom_top_left.config(bg=color_palette["light_green"])
            else:
                self.left_label.config(bg="white")
                self.left_bottom_top_left.config(bg="white")

            if self.right_label.cget("text") != "":
                self.right_label.config(bg=color_palette["light_green"])
                self.left_bottom_top_right.config(bg=color_palette["light_green"])
            else:
                self.right_label.config(bg="white")
                self.left_bottom_top_right.config(bg="white")
            self.remaining_amount_label.config(fg="black")
        else:
            self.table_canvas.set_active_rect_color(color_palette["active_rect"])
            self.left_label.config(bg="white")
            self.left_bottom_top_left.config(bg="white")
            self.right_label.config(bg="white")
            self.left_bottom_top_right.config(bg="white")
            self.remaining_amount_label.config(fg=color_palette["blink_black_text"])

        self.blink_job = self.root.after(BLINK_INTERVAL, self.blink)

    def update_table(
        self, active_row: int, active_col: int, amount_rows: int, amount_cols: int
    ) -> None:
        if self.blink_job is not None:
            self.root.after_cancel(self.blink_job)
            self.blink_job = None

        self.table_canvas.draw_table(active_row, active_col, amount_rows, amount_cols)
        self.blink_state = False
        self.blink()

    def show_item(self, item: dict[str, float | str]) -> None:
        # Update labels
        self.name_label.change_text(str(item["name"]))
        self.id_label.change_text(f"ID: {item['id']}")
        self.remaining_amount_label.change_text(f"{int(item['amount'])}")
        self.complete_amount_label.change_text(f"({self.dictionary['from']} {int(item['amount'])})")

        if self.load_cell_usage is True:
            self.from_gui_queue.put({"event": "New weight", "value": float(item["weight"])})
        box_str: str = ""
        if item["orientation"] == "Left_Side":
            box_str += "L"
        else:
            box_str += "R"
        box_str += str(item["row_idx"])
        box_str += "."
        box_str += str(item["col_idx"])
        self.from_gui_queue.put({"event": "New box", "value": box_str})

        self.current_picked_amount = 0

        # Refresh table
        self.update_table(
            int(item["row_idx"]),
            int(item["col_idx"]),
            int(item["row_amount"]),
            int(item["col_amount"]),
        )

        # Determine image path
        folder: str = ""
        if item["orientation"] == "Left_Side":
            folder = "img/Left_Side"
            self.left_label.change_text(self.dictionary["left_side"])
            self.left_label.config(bg=color_palette["light_green"])
            self.left_bottom_top_left.config(bg=color_palette["light_green"])
            self.right_label.change_text("")
            self.right_label.config(bg="white")
            self.left_bottom_top_right.config(bg="white")
        else:
            folder = "img/Right_Side"
            self.left_label.change_text("")
            self.left_label.config(bg="white")
            self.left_bottom_top_left.config(bg="white")
            self.right_label.change_text(self.dictionary["right_side"])
            self.right_label.config(bg=color_palette["light_green"])
            self.left_bottom_top_right.config(bg=color_palette["light_green"])
        img_path: str = os.path.join(folder, f"{item['id']}.jpg")

        self.img_label.load_image(img_path)

    def next_item(self) -> None:
        if self.items is not None:
            self.index += 1
            if self.index >= len(self.items):
                self.current_picked_amount = 0
                self.vehicle_name = None
                self.calibration_load_cell_active = False
                self.error_active = False
                self.items = None
                self.index = 0
                self.blink_job = None
                self.blink_state = False
                self.show_content_hint()
                self.content_hint.change_text(self.dictionary["content_new_vehicle"])
                self.status_text.change_text(self.dictionary["status_new_vehicle"])
                self.from_gui_queue.put({"event": "Vehicle complete", "value": True})
            else:
                self.show_item(self.items[self.index])

    def previous_item(self) -> None:
        if self.items is not None:
            self.index -= 1
            if self.index < 0:
                self.index = 0
            self.show_item(self.items[self.index])

    def check_pick_location(self, mcp_index: int, pins: list[int]) -> tuple[bool, bool]:
        """
        Check that the right box was picked.
        """
        if self.items is not None:
            current_item = self.items[self.index]

            target_mcp: float = float(current_item["row_idx"])
            target_pin: float = float(current_item["col_idx"])
            if current_item["orientation"] == "Left_Side":
                target_pin += 8

            if mcp_index == target_mcp:
                correct_pin_contained: bool = False
                wrong_pin_contained: bool = False
                for pin in pins:
                    if pin != target_pin:
                        wrong_pin_contained = True
                    else:
                        correct_pin_contained = True
                return correct_pin_contained, wrong_pin_contained
        if len(pins) > 0:
            return False, True
        else:
            return False, False

    def get_parts_for_vehicle(self, tag_id: str) -> dict[str, list[list[dict[str, float | str]]]]:
        return self.database.get(tag_id, {})

    def update_gui(self) -> None:
        try:
            needed: int = 0
            remaining: int = 0
            added_amount: int = 0

            while True:
                msg = self.to_gui_queue.get_nowait()
                event_type = msg.get("event")
                value = msg.get("value")

                if event_type == "Picking canceled":
                    self.current_picked_amount = 0
                    self.vehicle_name = None
                    self.calibration_load_cell_active = False
                    self.error_active = False
                    self.items = None
                    self.index = 0
                    self.blink_job = None
                    self.blink_state = False
                    self.show_content_hint()
                    self.content_hint.change_text(self.dictionary["content_canceled"])
                    self.traffic_canvas.draw_traffic_light("green")
                    self.status_text.change_text(self.dictionary["status_canceled"])

                if self.error_active is True:
                    if event_type == "Button short pressed" or event_type == "Button long pressed":
                        self.error_active = False
                        self.traffic_canvas.draw_traffic_light("green")
                        self.status_text.change_text(self.dictionary["status_error_acknowledged"])
                        self.from_gui_queue.put({"event": "Error cleared", "value": True})
                    continue

                if event_type == "All calibrations completed":
                    self.starting_calibrations_completed = True
                    if self.vehicle_name is not None and self.calibration_load_cell_active is False:
                        self.show_main_content()
                        self.traffic_canvas.draw_traffic_light("green")
                        self.status_text.change_text(self.dictionary["status_take_item"])
                    else:
                        self.show_content_hint()
                        if self.calibration_load_cell_active is False:
                            self.content_hint.change_text(self.dictionary["content_rfid_hint"])
                            self.traffic_canvas.draw_traffic_light("green")
                            self.status_text.change_text(self.dictionary["status_rfid"])

                # 1. RFID detection
                elif event_type == "RFID detected":
                    self.vehicle_name = value
                    self.items = self.flatten_data(self.get_parts_for_vehicle(value))
                    self.index = 0
                    if self.starting_calibrations_completed:
                        self.show_main_content()
                        # self.traffic_canvas.draw_traffic_light("green")
                        self.status_text.change_text(self.dictionary["status_take_item"])

                # 2. Calibration of the scale
                elif event_type == "Start Load Cell Calibration":
                    self.calibration_load_cell_active = True
                    self.show_content_hint()
                    self.content_hint.change_text(self.dictionary["content_lc_calibration"])
                    self.traffic_canvas.draw_traffic_light("yellow")
                    self.status_text.change_text(self.dictionary["status_lc_calib_start"])
                elif event_type == "Arduino ready for taring":
                    self.status_text.change_text(self.dictionary["status_lc_taring"])
                elif event_type == "Arduino ready for 200g confirmation":
                    self.status_text.change_text(self.dictionary["status_lc_calib_weight"])
                elif event_type == "Arduino ready for second taring":
                    self.status_text.change_text(self.dictionary["stauts_lc_sec_taring"])
                elif event_type == "Load cell calibration complete":
                    self.calibration_load_cell_active = False
                    if self.vehicle_name is None:
                        self.show_content_hint()
                        self.content_hint.change_text(self.dictionary["content_rfid_hint"])
                        self.traffic_canvas.draw_traffic_light("green")
                        self.status_text.change_text(self.dictionary["status_rfid"])
                    else:
                        self.show_main_content()
                        self.traffic_canvas.draw_traffic_light("green")
                        self.status_text.change_text(self.dictionary["status_lc_calib_finished"])

                if self.items is None:
                    continue

                if not self.calibration_load_cell_active:
                    if event_type == "Button short pressed":
                        self.status_text.change_text(self.dictionary["manual_next_item"])
                        # self.traffic_canvas.draw_traffic_light("green")
                        self.next_item()
                    elif event_type == "Button long pressed":
                        self.status_text.change_text(self.dictionary["manual_previous_item"])
                        # self.traffic_canvas.draw_traffic_light("green")
                        self.previous_item()

                # 3. Intrusion detection (light barrier)
                if "MCP-Handle detected" in event_type:
                    # Parse MCP index from the string "MCP handle detected at MCP X"
                    try:
                        mcp_idx: int = int(event_type.split("MCP")[-1].strip())
                    except ValueError:
                        continue

                    correct_pin_contained: bool = False
                    wrong_pin_contained: bool = False
                    correct_pin_contained, wrong_pin_contained = self.check_pick_location(
                        mcp_idx, value
                    )
                    if wrong_pin_contained:
                        self.error_active = True
                        # self.play_error_sound_as_user()
                        # self.error_sound.play()
                        self.status_text.change_text(self.dictionary["status_wrong_module"])
                        self.traffic_canvas.draw_traffic_light("red")
                        self.from_gui_queue.put({"event": "Error occurred", "value": True})
                    elif correct_pin_contained:
                        if self.load_cell_usage is True:
                            self.status_text.change_text(self.dictionary["status_correct_module"])
                            # self.traffic_canvas.draw_traffic_light("green")
                        else:
                            self.current_picked_amount += 2
                            needed = int(self.items[self.index]["amount"])
                            if self.current_picked_amount >= needed:
                                self.status_text.change_text(self.dictionary["status_all_picked"])
                                # self.traffic_canvas.draw_traffic_light("green")
                                self.next_item()
                            else:
                                remaining = needed - self.current_picked_amount
                                self.status_text.change_text(
                                    f"{self.dictionary['status_some_picked']}"
                                )
                                self.remaining_amount_label.change_text(f"{remaining}")

                # 4. Scales (weight change)
                elif event_type == "Weight Change":
                    needed = int(self.items[self.index]["amount"])
                    added_amount = int(value)
                    self.current_picked_amount += added_amount

                    if self.current_picked_amount == needed:
                        self.status_text.change_text(self.dictionary["status_correct_weight"])
                        # self.traffic_canvas.draw_traffic_light("green")
                        self.next_item()
                    elif self.current_picked_amount < needed:
                        remaining = needed - self.current_picked_amount
                        if added_amount == 1:
                            self.status_text.change_text(
                                f"{added_amount} {self.dictionary['status_some_weight_1']}"
                            )
                        else:
                            self.status_text.change_text(
                                f"{added_amount} {self.dictionary['status_some_weight']}"
                            )
                        self.remaining_amount_label.change_text(f"{remaining}")
                    else:
                        self.current_picked_amount -= added_amount
                        self.error_active = True
                        # self.play_error_sound_as_user()
                        # self.error_sound.play()
                        self.status_text.change_text(self.dictionary["status_too_much_weight"])
                        self.traffic_canvas.draw_traffic_light("red")
                        self.from_gui_queue.put({"event": "Error occurred", "value": True})

        except queue.Empty:
            pass

        self.root.after(100, self.update_gui)

    def on_closing(self) -> None:
        self.stop_event.set()
        self.root.destroy()


def start_viewer(
    to_gui_queue: mpQueue,
    from_gui_queue: mpQueue,
    database: dict[str, dict[str, list[list[dict[str, float | str]]]]],
    dictionary: dict[str, str],
    stop_event: mpEvent,
    load_cell_usage: bool,
) -> None:
    root: tk.Tk = tk.Tk()
    viewer: PartViewer = PartViewer(
        root, to_gui_queue, from_gui_queue, database, dictionary, stop_event, load_cell_usage
    )
    root.update()
    root.attributes("-fullscreen", True)
    root.after(100, viewer.update_gui)
    root.protocol("WM_DELETE_WINDOW", viewer.on_closing)
    root.mainloop()
