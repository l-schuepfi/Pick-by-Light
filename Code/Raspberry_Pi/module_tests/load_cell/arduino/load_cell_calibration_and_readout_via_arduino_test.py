"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to receive load cell outputs via USB from an arduino.

    The circuit shown in 'setup_load_cell_arduino_test.pdf' was set up for this test.

    The program leads through a calibration of the load cell using the push button.
    For calibration, the entire load must be removed, then a reference weight of 200.0g
    is applied and the load is removed again before stones may be placed on top.
    As soon as the load cell is calibrated, the program detects jumps and calculates
    the amount of added stones. The program ends when pressing Ctrl + C.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import pigpio
import serial


def button_callback(gpio: int, level: int, tick: int) -> None:
    global arduino_ready, state, print_output

    if level == 1:
        if arduino_ready is True:
            state += 1
            print_output = True


ser: serial.Serial = serial.Serial("/dev/ttyACM0", 57600, timeout=2)
time.sleep(2)

GPIO_BUTTON = 26

# Parameter
# STONE_WEIGHT = 0.1088  # g (Round yellow 1x1 brick)
STONE_WEIGHT = 0.7661  # g (Blue brick)
STABLE_TOLERANCE = 0.02  # g
STABLE_SAMPLES = 5

# States & Values
state: int = 0
print_output: bool = True
arduino_ready: bool = False

current_weight: float = 0.0
min_w: float = 0.0
max_w: float = 0.0
current_range: float = 0.0
diff: float = 0.0
stone_diff: int = 0
last_confirmed_weight: float = 0.0
buffer: list[float] = [0.0] * STABLE_SAMPLES
buffer_index: int = 0

pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not accessible")

pi.set_mode(GPIO_BUTTON, pigpio.INPUT)
pi.set_pull_up_down(GPIO_BUTTON, pigpio.PUD_OFF)
pi.set_glitch_filter(GPIO_BUTTON, 3000)  # Bounce time: 3000 µs = 3 ms

cb: pigpio._callback = pi.callback(GPIO_BUTTON, pigpio.EITHER_EDGE, button_callback)

print("Wait for keystrokes (Ctrl+C to exit)")
try:
    line: str = ""
    while arduino_ready is False:
        ser.write(b"c\n")
        line = ser.readline().decode("utf-8").strip()
        if line == "Start calibration (tare)":
            arduino_ready = True

    while True:
        if print_output is True:
            if state == 0:
                print("Remove any weight from the scale. Then press the button.")
                print_output = False
            elif state == 1:
                ser.write(b"t\n")
                arduino_ready = False
                while arduino_ready is False:
                    line = ser.readline().decode("utf-8").strip()
                    if line == "Calibration (200.0g)":
                        arduino_ready = True
                print("Add 200.0g of weight to the scale. Then press the button.")
                print_output = False
            elif state == 2:
                ser.write(b"200.0\n")
                arduino_ready = False
                while arduino_ready is False:
                    line = ser.readline().decode("utf-8").strip()
                    if line == "End calibration":
                        arduino_ready = True
                print("Calibration complete.")
                print("Remove the weights again. Then press the button.")
                print_output = False
            elif state == 3:
                ser.write(b"t\n")
                print("System ready. Please place stones on top.")
                state += 1
            elif state >= 4:
                line = ser.readline().decode("utf-8").strip()
                if "Load_cell output val: " in line:
                    current_weight = float(line.lstrip("Load_cell output val: "))
                    # print(f"Current weight: {current_weight}")
                    buffer[buffer_index] = current_weight
                    buffer_index = (buffer_index + 1) % STABLE_SAMPLES

                    # Check stability (wait until settled after change)
                    min_w = min(buffer)
                    max_w = max(buffer)
                    current_range = max_w - min_w

                    if current_range < STABLE_TOLERANCE:
                        diff = current_weight - last_confirmed_weight
                        if abs(diff) > (STONE_WEIGHT * 0.5):
                            stone_diff = round(diff / STONE_WEIGHT)

                            if stone_diff != 0:
                                if stone_diff > 0:
                                    print(f"Added: {stone_diff}", end="")
                                else:
                                    print(f"Taken from: {abs(stone_diff)}", end="")
                                print(f" | Diff: {diff:.4f} g")

                        last_confirmed_weight = current_weight

        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    cb.cancel()
    pi.stop()
