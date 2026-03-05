"""

    Pick-by-Light System
    -------------------------------------------------------------------------------
    Main programm for Raspberry Pi to control a Pick-by-Light system based on a
    infrared reflection principle. After calibration, the vehicle to be collected
    can be chosen via a rfid readout. Handles can then be detected via the MCP23017
    communication. Also, the load cell delivers the amount of added components.
    With these information, the system can automatically change to the next item.
    Above the current item box, LEDs light up to help the user.

    The database is loaded from an excel file to allow simple changements.

    The load cell can be calibrated before the picking of items has started by long
    pressing the push button. Errors can be acknowledged by pushing the push button.
    You can manually change to the nex item by pushing the button for a short time.
    When pushing the button for a longer time (> 2 seconds), it switches to the
    previous item. The communication with the GUI class is done via 'to_qui_queue'
    and 'from_gui_queue'.

    The program is using an extra thread-loop for retrieving the sensor values as
    the GUI also needs to run as a loop.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import multiprocessing as mp
import queue
import time
from multiprocessing.context import Process as mpProcess
from multiprocessing.queues import Queue as mpQueue
from multiprocessing.synchronize import Event as mpEvent

import board
import pigpio

from gui import start_viewer
from lego_database import read_excel_matrices
from load_cell import LoadCell
from mcp23017 import MCP23017
from rafi_press_button import RAFI_Push_Button
from rfid_reader import RFIDReader
from texts import texts
from ws2812b_led_strip import WS2812B, RGB_Color

# Language
language: str = "de"

# Usage of load cell
USE_LOAD_CELL = True

# Constants / Hardware assignments
MCP_INTERRUPT_PINS = [4, 17, 27, 22, 16, 24, 23]
LED_COUNT_LARGE_STRIP = 865  # Number of LEDs in the large strip
LED_COUNT_SHORT_STRIP = 15  # Number of LEDs in the short strip
RED = RGB_Color(255, 0, 0)
YELLOW = RGB_Color(255, 255, 0)
GREEN = RGB_Color(0, 255, 0)


def setup(
    dictionary: dict[str, str], push_button_queue: mpQueue, load_cell_usage: bool
) -> tuple[
    pigpio.pi,
    list[MCP23017],
    WS2812B,
    WS2812B,
    RAFI_Push_Button,
    RFIDReader,
    LoadCell | None,
    dict[str, dict[str, list[list[dict[str, float | str]]]]],
]:
    # Initialize pigpio
    pi: pigpio.pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError(dictionary["pigpio_not_connected"])

    # MCP instances
    mcps: list[MCP23017] = [
        MCP23017(idx, 1, int_pin, pi) for idx, int_pin in enumerate(MCP_INTERRUPT_PINS)
    ]

    large_led_strip: WS2812B = WS2812B(board.D12, LED_COUNT_LARGE_STRIP)
    short_led_strip: WS2812B = WS2812B(board.D13, LED_COUNT_SHORT_STRIP)

    push_button: RAFI_Push_Button = RAFI_Push_Button(push_button_queue, 26, pi)

    rfid_reader: RFIDReader = RFIDReader()

    load_cell: LoadCell | None = None
    if load_cell_usage is True:
        load_cell = LoadCell()

    database: dict[str, dict[str, list[list[dict[str, float | str]]]]] = read_excel_matrices(
        "data/Fahrzeuge_Stueckzahluebersicht.xlsx"
    )

    return pi, mcps, large_led_strip, short_led_strip, push_button, rfid_reader, load_cell, database


def light_up_leds_on_side(short_led_strip: WS2812B, side: str) -> None:
    if side.lower() == "left":
        short_led_strip.light_up([(idx, GREEN) for idx in range(8, 15)])
    elif side.lower() == "right":
        short_led_strip.light_up([(idx, GREEN) for idx in range(0, 8)])


def measure_loop_without_load_cell(
    to_gui_queue: mpQueue,
    from_gui_queue: mpQueue,
    mcps: list[MCP23017],
    large_led_strip: WS2812B,
    short_led_strip: WS2812B,
    push_button_queue: mpQueue,
    rfid_reader: RFIDReader,
    stop_signal: mpEvent,
) -> None:
    """
    This function should run in a thread parallel to the GUI.
    """
    push_button_press_time: float | None = None
    button_press_duration: float = 0.0
    rfid_read_complete: bool = False
    push_button_short_pressed: bool = False
    first_short_press_detected: bool = False
    second_short_press_detected: bool = False
    mcp_calibration_finished: bool = False
    rfid_wait_for_exchange: bool = False
    actual_side: str = "Left"

    try:
        while not stop_signal.is_set():
            try:
                while True:
                    msg = from_gui_queue.get_nowait()
                    event_type = msg.get("event")
                    value = msg.get("value")

                    if event_type == "New box":
                        actual_side = "Left" if value.startswith("L") else "Right"
                        row: int = int(value.split(".")[0][-1])
                        column: int = int(value.split(".")[1][0])
                        # print(f"Row: {row}")
                        # print(f"Column: {column}")
                        light_up_leds_on_side(short_led_strip, actual_side)
                        light_up_leds_from_position(large_led_strip, actual_side, row, column)
                        # print("New LEDs lighting")
                    elif event_type == "Vehicle complete":
                        push_button_press_time = None
                        rfid_read_complete = False
                        push_button_short_pressed = False
                        first_short_press_detected = False
                        second_short_press_detected = False
                        rfid_wait_for_exchange = True
                        large_led_strip.turn_off()
                    elif event_type == "Error cleared":
                        light_up_leds_on_side(short_led_strip, actual_side)
                    elif event_type == "Error occurred":
                        short_led_strip.light_up_all(RED)

            except queue.Empty:
                pass

            # Calibration (at the beginning)
            if not mcp_calibration_finished:
                all_mcp_calibrated: bool = True
                for idx, mcp in enumerate(mcps):
                    mcp.update()
                    if not mcp.is_calibration_finished():
                        all_mcp_calibrated = False
                if all_mcp_calibrated:
                    # print("MCPs calibrated")
                    # for idx, mcp in enumerate(mcps):
                    #     mcp.print_calibration_values(idx)

                    mcp_calibration_finished = True
                    to_gui_queue.put({"event": "All calibrations completed", "value": True})

            if mcp_calibration_finished and not rfid_read_complete:
                rfid_detected: bool = False
                for _ in range(3):
                    uid: list[int] | None = rfid_reader.read_tag(False)
                    # print(uid)
                    if uid:
                        rfid_detected = True
                        if rfid_wait_for_exchange is False:
                            # print("RFID detection")
                            tag: str = ""
                            if uid == [136, 4, 64, 178, 126]:
                                tag = "Muscle_Car"
                            elif uid == [136, 4, 68, 178, 122]:
                                tag = "Lamborghini"
                            elif uid == [136, 4, 209, 167, 250]:
                                tag = "McLaren"
                            else:
                                # print("Fehler: Unbekannte UID.")
                                raise ValueError("Unbekannte UID.")

                            to_gui_queue.put({"event": "RFID detected", "value": tag})
                            rfid_read_complete = True
                            break
                if rfid_wait_for_exchange is True and rfid_detected is False:
                    # print("Kein RFID mehr erkannt")
                    rfid_wait_for_exchange = False

            # Distinguish between long and short button presses (and double short presses)
            actual_time: float = time.monotonic()
            if push_button_press_time is not None:
                if first_short_press_detected is True:
                    button_press_duration = actual_time - push_button_press_time
                    if button_press_duration > 0.5:
                        push_button_press_time = None
                        first_short_press_detected = False
                        push_button_short_pressed = True
                elif second_short_press_detected is True:
                    button_press_duration = actual_time - push_button_press_time
                    if button_press_duration > 0.5:
                        push_button_press_time = None
                        second_short_press_detected = False
                elif actual_time - push_button_press_time > 2:
                    button_press_duration = actual_time - push_button_press_time
                    push_button_press_time = None
                    if rfid_read_complete is True:
                        to_gui_queue.put(
                            {
                                "event": "Button long pressed",
                                "value": button_press_duration,
                            }
                        )
                        # print("Button long pressed")

            if not push_button_queue.empty():
                button_event = push_button_queue.get()
                if button_event[0] == 0:
                    if push_button_press_time:
                        button_press_duration = button_event[1] - push_button_press_time
                        if second_short_press_detected is True:
                            large_led_strip.turn_off()
                            short_led_strip.light_up_all(GREEN)
                            to_gui_queue.put(
                                {
                                    "event": "Picking canceled",
                                    "value": button_press_duration,
                                }
                            )
                            # print("Button double short pressed")
                            push_button_press_time = None
                            rfid_read_complete = False
                            push_button_short_pressed = False
                            first_short_press_detected = False
                            second_short_press_detected = False
                            rfid_wait_for_exchange = True
                        elif first_short_press_detected is False:
                            push_button_press_time = button_event[1]
                            first_short_press_detected = True
                else:
                    push_button_press_time = button_event[1]
                    if first_short_press_detected is True:
                        first_short_press_detected = False
                        second_short_press_detected = True
                    # print(f"Press time: {push_button_press_time}")

            if push_button_short_pressed is True and button_event is not None:
                to_gui_queue.put(
                    {
                        "event": "Button short pressed",
                        "value": button_press_duration,
                    }
                )
                # print("Button short pressed")
                push_button_short_pressed = False

            # Started gathering
            if mcp_calibration_finished and rfid_read_complete:
                for idx, mcp in enumerate(mcps):
                    handles = mcp.update(True)
                    # handles = mcp.test_update(idx, 6, 6)
                    if len(handles) > 0:
                        # print(f"MCP-Handle detected at MCP {idx}: {handles}")
                        to_gui_queue.put(
                            {"event": f"MCP-Handle detected at MCP {idx}", "value": handles}
                        )

            time.sleep(0.001)
    except KeyboardInterrupt:
        pass


def measure_loop_with_load_cell(
    to_gui_queue: mpQueue,
    from_gui_queue: mpQueue,
    mcps: list[MCP23017],
    large_led_strip: WS2812B,
    short_led_strip: WS2812B,
    push_button_queue: mpQueue,
    rfid_reader: RFIDReader,
    load_cell: LoadCell,
    stop_signal: mpEvent,
) -> None:
    """
    This functiuon should run in a thread parallel to the GUI.
    """
    push_button_press_time: float | None = None
    button_press_duration: float = 0.0
    rfid_read_complete: bool = False
    load_cell_ready: bool = False
    load_cell_in_calibration: bool = False
    load_cell_calibration_state: int = 0
    push_button_short_pressed: bool = False
    first_short_press_detected: bool = False
    second_short_press_detected: bool = False
    arduino_ready_for_calibration_step: bool = False
    mcp_calibration_finished: bool = False
    component_weight: float | None = None
    box_handle_detected: bool = False
    rfid_wait_for_exchange: bool = False
    load_cell_thread_started: bool = False
    calib_time: float = 0.0
    actual_side: str = "Left"

    from_measure_queue: mpQueue = mp.Queue()

    load_cell_thread: mpProcess = mp.Process(
        target=load_cell_loop,
        args=(
            to_gui_queue,
            from_measure_queue,
            load_cell,
            stop_signal,
        ),
    )

    try:
        while not stop_signal.is_set():
            try:
                while True:
                    msg: dict[str, str] = from_gui_queue.get_nowait()
                    event_type: str | None = msg.get("event")
                    value: str | None = msg.get("value")

                    if event_type is None or value is None:
                        continue

                    if event_type == "New weight":
                        component_weight = value
                        from_measure_queue.put({"event": "New weight", "value": component_weight})
                        # print(f"New component weight: {component_weight}")
                    elif event_type == "New box":
                        actual_side = "Left" if value.startswith("L") else "Right"
                        row = int(value.split(".")[0][-1])
                        column = int(value.split(".")[1][0])
                        # print(f"Row: {row}")
                        # print(f"Column: {column}")
                        light_up_leds_on_side(short_led_strip, actual_side)
                        light_up_leds_from_position(large_led_strip, actual_side, row, column)
                        # print("New LEDs lighting")
                    elif event_type == "Vehicle complete":
                        push_button_press_time = None
                        rfid_read_complete = False
                        load_cell_in_calibration = False
                        load_cell_calibration_state = 0
                        push_button_short_pressed = False
                        first_short_press_detected = False
                        second_short_press_detected = False
                        arduino_ready_for_calibration_step = False
                        component_weight = None
                        box_handle_detected = False
                        rfid_wait_for_exchange = True
                        large_led_strip.turn_off()
                        if load_cell_thread.is_alive():
                            load_cell_thread.join(timeout=2)
                            if load_cell_thread.is_alive():
                                load_cell_thread.terminate()
                        load_cell_thread_started = False
                    elif event_type == "Error cleared":
                        light_up_leds_on_side(short_led_strip, actual_side)
                    elif event_type == "Error occurred":
                        short_led_strip.light_up_all(RED)

            except queue.Empty:
                pass

            # Calibration (at the beginning)
            if not mcp_calibration_finished:
                all_mcp_calibrated: bool = True
                for idx, mcp in enumerate(mcps):
                    mcp.update()
                    if not mcp.is_calibration_finished():
                        all_mcp_calibrated = False
                if all_mcp_calibrated:
                    # print("MCPs calibrated")
                    # for idx, mcp in enumerate(mcps):
                    #     mcp.print_calibration_values(idx)

                    mcp_calibration_finished = True
                    if load_cell_ready:
                        to_gui_queue.put({"event": "All calibrations completed", "value": True})

            if not load_cell_ready:
                load_cell.tare()
                if load_cell.tare_complete():
                    load_cell_ready = True
                    # print("Load cell ready")
                    if mcp_calibration_finished:
                        to_gui_queue.put({"event": "All calibrations completed", "value": True})

            if mcp_calibration_finished and not rfid_read_complete and load_cell_ready:
                rfid_detected: bool = False
                for _ in range(3):
                    uid = rfid_reader.read_tag(False)
                    # print(uid)
                    if uid:
                        rfid_detected = True
                        if rfid_wait_for_exchange is False:
                            # print("RFID detection")
                            if uid == [136, 4, 64, 178, 126]:
                                tag = "Muscle_Car"
                            elif uid == [136, 4, 68, 178, 122]:
                                tag = "Lamborghini"
                            elif uid == [136, 4, 209, 167, 250]:
                                tag = "McLaren"
                            else:
                                # print("Fehler: Unbekannte UID.")
                                raise ValueError("Unbekannte UID.")

                            if not load_cell_in_calibration:
                                load_cell.tare()
                            to_gui_queue.put({"event": "RFID detected", "value": tag})
                            rfid_read_complete = True
                            arduino_ready_for_calibration_step = True
                            break
                if rfid_wait_for_exchange is True and rfid_detected is False:
                    # print("Kein RFID mehr erkannt")
                    rfid_wait_for_exchange = False

            # Distinguish between long and short button presses (and double short presses)
            actual_time: float = time.monotonic()
            if push_button_press_time is not None:
                if first_short_press_detected is True:
                    button_press_duration = actual_time - push_button_press_time
                    if button_press_duration > 0.5:
                        push_button_press_time = None
                        first_short_press_detected = False
                        push_button_short_pressed = True
                elif second_short_press_detected is True:
                    button_press_duration = actual_time - push_button_press_time
                    if button_press_duration > 0.5:
                        push_button_press_time = None
                        second_short_press_detected = False
                elif actual_time - push_button_press_time > 2:
                    button_press_duration = actual_time - push_button_press_time
                    push_button_press_time = None
                    if (
                        box_handle_detected is False
                        and rfid_read_complete is True
                        and load_cell_in_calibration is False
                    ):
                        load_cell_in_calibration = True
                        load_cell_calibration_state = 0
                    else:
                        to_gui_queue.put(
                            {
                                "event": "Button long pressed",
                                "value": button_press_duration,
                            }
                        )
                        # print("Button long pressed")

            if not push_button_queue.empty():
                button_event = push_button_queue.get()
                if button_event[0] == 0:
                    if push_button_press_time:
                        button_press_duration = button_event[1] - push_button_press_time
                        if second_short_press_detected is True:
                            if load_cell_ready:
                                load_cell.reset()
                            large_led_strip.turn_off()
                            short_led_strip.light_up_all(GREEN)
                            to_gui_queue.put(
                                {
                                    "event": "Picking canceled",
                                    "value": button_press_duration,
                                }
                            )
                            # print("Button double short pressed")
                            push_button_press_time = None
                            rfid_read_complete = False
                            load_cell_in_calibration = False
                            load_cell_calibration_state = 0
                            push_button_short_pressed = False
                            first_short_press_detected = False
                            second_short_press_detected = False
                            arduino_ready_for_calibration_step = False
                            component_weight = None
                            box_handle_detected = False
                            rfid_wait_for_exchange = True
                            if load_cell_thread.is_alive():
                                load_cell_thread.join(timeout=2)
                                if load_cell_thread.is_alive():
                                    load_cell_thread.terminate()
                            load_cell_thread_started = False
                        elif first_short_press_detected is False:
                            push_button_press_time = button_event[1]
                            first_short_press_detected = True
                else:
                    push_button_press_time = button_event[1]
                    if first_short_press_detected is True:
                        first_short_press_detected = False
                        second_short_press_detected = True
                    # print(f"Press time: {push_button_press_time}")

            # Calibration of the load cell
            if load_cell_in_calibration:
                if load_cell_calibration_state == 0:
                    load_cell.calibrate()
                    short_led_strip.light_up_all(YELLOW)
                    # print("Calibrate")
                    to_gui_queue.put({"event": "Start Load Cell Calibration", "value": True})
                    arduino_ready_for_calibration_step = False
                    load_cell_calibration_state += 1
                    calib_time = time.monotonic()
                if load_cell_calibration_state == 1:
                    if not arduino_ready_for_calibration_step:
                        if load_cell.is_arduino_ready() or time.monotonic() - calib_time > 1.0:
                            to_gui_queue.put({"event": "Arduino ready for taring", "value": True})
                            arduino_ready_for_calibration_step = True
                    elif push_button_short_pressed:
                        load_cell.next_calibration_status()
                        load_cell.tare()
                        arduino_ready_for_calibration_step = False
                        push_button_short_pressed = False
                        load_cell_calibration_state += 1
                if load_cell_calibration_state == 2:
                    if not arduino_ready_for_calibration_step:
                        if load_cell.is_arduino_ready():
                            to_gui_queue.put(
                                {"event": "Arduino ready for 200g confirmation", "value": True}
                            )
                            arduino_ready_for_calibration_step = True
                    elif push_button_short_pressed:
                        load_cell.next_calibration_status()
                        load_cell.confirm_200g()
                        arduino_ready_for_calibration_step = False
                        push_button_short_pressed = False
                        load_cell_calibration_state += 1
                if load_cell_calibration_state == 3:
                    if not arduino_ready_for_calibration_step:
                        if load_cell.is_arduino_ready():
                            to_gui_queue.put(
                                {"event": "Arduino ready for second taring", "value": True}
                            )
                            arduino_ready_for_calibration_step = True
                    elif push_button_short_pressed:
                        load_cell.tare()
                        load_cell.next_calibration_status()
                        arduino_ready_for_calibration_step = False
                        push_button_short_pressed = False
                        load_cell_calibration_state += 1
                if load_cell_calibration_state == 4:
                    if not arduino_ready_for_calibration_step:
                        if load_cell.is_arduino_ready():
                            light_up_leds_on_side(short_led_strip, actual_side)
                            to_gui_queue.put(
                                {"event": "Load cell calibration complete", "value": True}
                            )
                            arduino_ready_for_calibration_step = True
                            load_cell_in_calibration = False

            if push_button_short_pressed is True and button_event is not None:
                to_gui_queue.put(
                    {
                        "event": "Button short pressed",
                        "value": button_press_duration,
                    }
                )
                # print("Button short pressed")
                push_button_short_pressed = False

            # Started gathering
            if (
                mcp_calibration_finished
                and load_cell_ready
                and not load_cell_in_calibration
                and rfid_read_complete
            ):
                for idx, mcp in enumerate(mcps):
                    handles = mcp.update()
                    # handles = mcp.test_update(idx, 6, 6)
                    if len(handles) > 0:
                        box_handle_detected = True
                        # print(f"MCP-Handle detected at MCP {idx}: {handles}")
                        to_gui_queue.put(
                            {"event": f"MCP-Handle detected at MCP {idx}", "value": handles}
                        )
                if (
                    component_weight is not None
                    and load_cell_thread_started is False
                    and box_handle_detected is True
                ):
                    load_cell_thread_started = True
                    load_cell_thread = mp.Process(
                        target=load_cell_loop,
                        args=(
                            to_gui_queue,
                            from_measure_queue,
                            load_cell,
                            stop_signal,
                        ),
                    )
                    load_cell_thread.start()

            time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        if load_cell_thread_started is True:
            load_cell_thread.join()


def measure_loop(
    to_gui_queue: mpQueue,
    from_gui_queue: mpQueue,
    mcps: list[MCP23017],
    large_led_strip: WS2812B,
    short_led_strip: WS2812B,
    push_button_queue: mpQueue,
    rfid_reader: RFIDReader,
    load_cell: LoadCell | None,
    stop_signal: mpEvent,
) -> None:
    """
    This functiuon should run in a thread parallel to the GUI.
    """
    if load_cell is None:
        measure_loop_without_load_cell(
            to_gui_queue,
            from_gui_queue,
            mcps,
            large_led_strip,
            short_led_strip,
            push_button_queue,
            rfid_reader,
            stop_signal,
        )
    else:
        measure_loop_with_load_cell(
            to_gui_queue,
            from_gui_queue,
            mcps,
            large_led_strip,
            short_led_strip,
            push_button_queue,
            rfid_reader,
            load_cell,
            stop_signal,
        )


def load_cell_loop(
    to_gui_queue: mpQueue,
    from_measure_queue: mpQueue,
    load_cell: LoadCell,
    stop_signal: mpEvent,
) -> None:
    weight: float | None = None

    try:
        while not stop_signal.is_set():
            try:
                while True:
                    msg = from_measure_queue.get_nowait()
                    event_type = msg.get("event")
                    value = msg.get("value")
                    if event_type == "New weight":
                        weight = value

            except queue.Empty:
                pass

            if weight is not None:
                # load_cell.test_determine_amount_of_added_elements(0.1088)
                # load_cell.test_determine_amount_of_added_elements(0.4974)
                # load_cell.test_determine_amount_of_added_elements(1.0692)
                # load_cell.test_determine_amount_of_added_elements(1.4171)
                detected_count = load_cell.determine_amount_of_added_elements(weight)
                if detected_count != 0:
                    # print(f"Detected count: {detected_count}")
                    to_gui_queue.put({"event": "Weight Change", "value": detected_count})

            time.sleep(0.001)
    except KeyboardInterrupt:
        pass


def light_up_leds_from_position(
    led_strip: WS2812B, side: str = "Left", row: int = 1, column: int = 1
) -> None:
    if side.lower() not in ("left", "right"):
        return
    if row < 0 or row >= 7:
        return
    if column < 0 or column >= 7:
        return

    start_led_indices = {
        "left": [
            [432, 440, 449, 458, 468, 477, 486],
            [548, 539, 530, 520, 511, 502, 494],
            [556, 564, 573, 583, 592, 601, 610],
            [672, 663, 653, 644, 635, 626, 618],
            [680, 688, 698, 707, 716, 725, 734],
            [796, 787, 778, 769, 759, 750, 742],
            [804, 812, 821, 830, 839, 847, 856],
        ],
        "right": [
            [371, 379, 388, 397, 406, 416, 425],
            [363, 354, 344, 335, 326, 317, 309],
            [247, 255, 264, 273, 282, 292, 301],
            [239, 230, 220, 211, 202, 193, 185],
            [124, 131, 140, 149, 158, 167, 176],
            [115, 106, 97, 88, 79, 70, 62],
            [0, 8, 17, 26, 35, 44, 53],
        ],
    }

    end_led_indices = {
        "left": [
            [439, 448, 457, 467, 476, 485, 493],
            [555, 547, 538, 529, 519, 510, 501],
            [563, 572, 582, 591, 600, 609, 617],
            [679, 671, 662, 652, 643, 634, 625],
            [687, 697, 706, 715, 724, 733, 741],
            [803, 795, 786, 777, 768, 758, 749],
            [811, 820, 829, 838, 846, 855, 864],
        ],
        "right": [
            [378, 387, 396, 405, 415, 424, 431],
            [370, 362, 353, 343, 334, 325, 316],
            [254, 263, 272, 281, 291, 300, 308],
            [246, 238, 229, 219, 210, 201, 192],
            [130, 139, 148, 157, 166, 175, 184],
            [123, 114, 105, 96, 87, 78, 69],
            [7, 16, 25, 34, 43, 52, 61],
        ],
    }

    begin = start_led_indices[side.lower()][row][column]
    end = end_led_indices[side.lower()][row][column]

    led_list: list[tuple[int, RGB_Color]] = []
    for i in range(begin, end + 1):
        if i < led_strip.led_count:
            led_list.append((i, GREEN))
    led_strip.light_up(led_list)


def main() -> pigpio.pi:
    dictionary: dict[str, str] = texts[language]

    push_button_queue: mpQueue = mp.Queue()
    (
        pi,
        mcps,
        large_led_strip,
        short_led_strip,
        push_button,
        rfid_reader,
        load_cell,
        database,
    ) = setup(dictionary, push_button_queue, USE_LOAD_CELL)

    large_led_strip.turn_off()
    short_led_strip.light_up_all(GREEN)

    # Queue for the communication between the measure_loop and the gui_mainloop
    to_gui_queue: mpQueue = mp.Queue()
    from_gui_queue: mpQueue = mp.Queue()
    stop_signal: mpEvent = mp.Event()

    try:
        # Start new thread for measuring in parallel to the gui event loop
        thread: mpProcess = mp.Process(
            target=measure_loop,
            args=(
                to_gui_queue,
                from_gui_queue,
                mcps,
                large_led_strip,
                short_led_strip,
                push_button_queue,
                rfid_reader,
                load_cell,
                stop_signal,
            ),
            # daemon=True,
        )
        thread.start()

        # Open the GUI
        start_viewer(to_gui_queue, from_gui_queue, database, dictionary, stop_signal, USE_LOAD_CELL)
    except KeyboardInterrupt:
        print("Ende")
    finally:
        stop_signal.set()
        if thread.is_alive():
            thread.join(timeout=2)
            if thread.is_alive():
                thread.terminate()

        # close connections from pi-object
        for mcp in mcps:
            mcp.close_connection()
        push_button.close_connection()

        large_led_strip.turn_off()
        short_led_strip.turn_off()
        return pi


if __name__ == "__main__":
    pi = main()
    pi.stop()
