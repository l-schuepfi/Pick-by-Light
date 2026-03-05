"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to detect added stones on a load cell on the pi.

    The circuit shown in 'setup_load_cell_pi_test.pdf' was set up for this test.

    Uses the output value of in the calibration script in the 'set_reference_unit'
    function. Then the program detects jumps and calculates the amount of added stones.
    The program ends when pressing Ctrl + C.

    As the values received are not stable enough, I would not recommend controlling a
    load cell directly via the Raspberry Pi. Instead, use an Arduino and receive correct
    values via a USB connection or a bus system (as shown in the Arduino folder).

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

from hx711_pigpio import HX711

# ===== Parameter =====
STONE_WEIGHT = 0.1088  # g (Round yellow 1x1 brick)
# STONE_WEIGHT = 0.7661  # g (Blue brick)
STABLE_TOLERANCE = 0.02  # g
STABLE_SAMPLES = 5

# ===== HX711 =====
hx: HX711 = HX711(5, 6)

time.sleep(2.0)  # Warm up

hx.set_reference_unit(-1039.87625)  # use calibration factor here
hx.tare()

normal_weight: float = hx.get_weight(20)

print("System ready. Please place stones on top.")

last_confirmed_weight: float = 0.0
buffer: list[float] = [0.0] * STABLE_SAMPLES
buffer_index: int = 0

current_weight: float = 0.0
min_w: float = 0.0
max_w: float = 0.0
current_range: float = 0.0
diff: float = 0.0
stone_diff: int = 0

while True:
    current_weight = hx.get_weight(1)
    if abs(current_weight - normal_weight) > 20 * STONE_WEIGHT:
        continue
    else:
        normal_weight = current_weight

    buffer[buffer_index] = current_weight
    buffer_index = (buffer_index + 1) % STABLE_SAMPLES

    # Check stability (wait until settled after change)
    min_w = min(buffer)
    max_w = max(buffer)
    current_range = max_w - min_w

    # print(f"Current: {current_weight:.4f} | Diff: {current_range:.4f}")

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

    time.sleep(0.01)
