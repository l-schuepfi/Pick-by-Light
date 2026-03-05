"""

    Pick-by-Light System
    ---------------------------------------------------------------------
    Class to handle the communication with the arduino for the load cell.
    It also allows to determine the amount of added stones.
    Therefore, it waits until the last X samples have a diff of at least
    the specified tolerance. Then the difference of the hole jump can be
    determined and with the information about the stone weight, the
    amount can be calculated.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import serial

STABLE_TOLERANCE = 0.02  # g
STABLE_SAMPLES = 5


class LoadCell:
    def __init__(self) -> None:
        self.ser: serial.Serial = serial.Serial("/dev/ttyACM0", 57600, timeout=2)
        time.sleep(2)

        self.is_in_calibration: bool = True
        self.state: int = 0

        self.current_weight: float | None = None
        self.last_confirmed_weight: float | None = None
        self.buffer: list[float | None] = [None] * STABLE_SAMPLES
        self.buffer_index = 0

    def calibrate(self) -> None:
        self.state = 0
        self.ser.write(b"c\n")

    def next_calibration_status(self) -> None:
        self.state += 1

    def is_arduino_ready(self) -> bool:
        line: str = ""
        while True:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                break
            except UnicodeDecodeError:
                continue
        if self.state == 0 and line == "Start calibration (tare)":
            return True
        elif self.state == 1 and line == "Calibration (200.0g)":
            return True
        elif self.state == 2 and line == "End calibration":
            return True
        elif self.state == 3 and line == "Tare complete":
            return True
        return False

    def reset(self) -> None:
        self.ser.write(b"r\n")
        self.is_in_calibration = False
        self.state = 0

    def tare(self) -> None:
        self.ser.write(b"t\n")
        # print(f"State: {self.state}")
        if self.state == 3:
            self.next_calibration_status()

    def tare_complete(self) -> bool:
        line: str = ""
        while True:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                break
            except UnicodeDecodeError:
                continue
        if line == "Tare complete":
            return True
        return False

    def confirm_200g(self) -> None:
        if self.state == 2:
            self.ser.write(b"200.0\n")

    def read_new_load_value(self) -> float | None:
        line: str = ""
        while True:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                break
            except UnicodeDecodeError:
                continue
        if "Load_cell output val: " in line:
            try:
                return float(line.lstrip("Load_cell output val: "))
            except ValueError:
                return None
        return None

    def detect_change(self) -> bool:
        self.current_weight = self.read_new_load_value()
        # print(self.current_weight)
        if self.current_weight:
            self.buffer[self.buffer_index] = self.current_weight
            self.buffer_index = (self.buffer_index + 1) % STABLE_SAMPLES
            if None in self.buffer:
                return False

            float_buffer: list[float] = [0.0] * STABLE_SAMPLES
            for idx, value in enumerate(self.buffer):
                if value is not None:
                    float_buffer[idx] = value

            # Check stability (wait until settled after change)
            min_w: float = min(float_buffer)
            max_w: float = max(float_buffer)
            current_range: float = max_w - min_w

            if current_range < STABLE_TOLERANCE:
                return True

        return False

    def determine_amount_of_added_elements(self, element_weight: float) -> int:
        amount_elements: int = 0
        if self.detect_change():
            if self.last_confirmed_weight and self.current_weight:
                diff: float = self.current_weight - self.last_confirmed_weight
                if abs(diff) > (element_weight * 0.5):
                    amount_elements = round(diff / element_weight)
            self.last_confirmed_weight = self.current_weight
        if amount_elements >= 0:
            return amount_elements
        else:
            return 0

    def test_determine_amount_of_added_elements(self, element_weight: float) -> int:
        amount_elements: int = 0
        change: bool = self.detect_change()
        print(f"Aktuelles Gewicht: {self.current_weight}")
        if change:
            if self.last_confirmed_weight and self.current_weight:
                diff: float = self.current_weight - self.last_confirmed_weight
                if abs(diff) > (element_weight * 0.5):
                    amount_elements = round(diff / element_weight)
            self.last_confirmed_weight = self.current_weight
        if amount_elements > 0:
            print(f"Hinzugefügte Teile: {amount_elements}")
            return amount_elements
        else:
            return 0

    def __del__(self) -> None:
        self.ser.close()
