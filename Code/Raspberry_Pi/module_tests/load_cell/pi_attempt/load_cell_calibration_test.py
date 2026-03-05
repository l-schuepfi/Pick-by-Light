"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to calibate a load cell directly on the pi.

    The circuit shown in 'setup_load_cell_pi_test.pdf' was set up for this test.

    The program leads through a calibration of the load cell. For calibration, the
    entire load must be removed, then a reference weight is applied (entry of weight in
    grams via the command line) and the load is removed again before load may be placed
    on top. The program ends when pressing Ctrl + C.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import sys
import time

import pigpio
from hx711_pigpio import HX711


def clean_and_exit(hx: HX711, pi: pigpio.pi) -> None:
    print("Cleaning...")
    hx.power_down()
    pi.stop()
    print("Bye!")
    sys.exit()


# Initialize pigpio
pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not running")

# HX711 to GPIO 5 (DOUT) and GPIO 6 (PD_SCK)
hx: HX711 = HX711(5, 6, pi=pi)
hx.read_long()

# Stabilization
time.sleep(2)
for _ in range(20):
    hx.read_long()

hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(1)

# hx.reset()
hx.tare()
offset: int | float = hx.read_average(20)
print(f"Raw value (zero point): {offset}")

print("Tare done! Add weight now...")

mass: float = float(input("Then send the weight of this mass (i.e. 100.0) via the command line: "))

raw: int | float = hx.read_average(20)
print(f"Raw value (with weight): {raw}")
ref: float = (raw - offset) / mass
hx.set_reference_unit(ref)
print("Calibrated:", ref)

val: float = 0.0
while True:
    try:
        val = hx.get_weight(10)
        print(val)
        time.sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        clean_and_exit(hx, pi)
