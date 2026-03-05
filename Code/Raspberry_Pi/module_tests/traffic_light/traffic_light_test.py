"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to control a traffic light module.

    The circuit shown in 'setup_traffic_light_test.pdf' was set up for this test.

    The test first turns on the red LED for 2 seconds,
    then the red and yellow LEDs for one second,
    and finally the green LED for one second before all LEDs are turned off again.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import pigpio


def traffic_light_phase(red: int, yellow: int, green: int) -> None:
    pi.write(ROT, red)
    pi.write(GELB, yellow)
    pi.write(GRUEN, green)


# Initialization
pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not accessible")

# Define pins
ROT = 14
GELB = 15
GRUEN = 20

# Set pins as output
for pin in [ROT, GELB, GRUEN]:
    pi.set_mode(pin, pigpio.OUTPUT)

try:
    # Example: Red phase
    traffic_light_phase(1, 0, 0)
    time.sleep(2)

    # Example: Yellow-red (preparation)
    traffic_light_phase(1, 1, 0)
    time.sleep(1)

    # Example: Green
    traffic_light_phase(0, 0, 1)
    time.sleep(2)

finally:
    # Turn off all lights when exiting
    traffic_light_phase(0, 0, 0)
    pi.stop()
