"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to check if a push button is pressed or released.

    The circuit shown in 'setup_push_button_test.pdf' was set up for this test.

    The test continuously checks whether the push button is pressed or released.
    In both cases, it outputs the detection. The program ends when pressing Ctrl + C.

    Author: Andreas Katzenberger
    Date: 2026-02-26

"""

import time

import pigpio


def button_callback(gpio: int, level: int, tick: int) -> None:
    if level == 0:
        print("Button LOSGELASSEN")
    elif level == 1:
        print("Button GEDRÜCKT")


GPIO_BUTTON = 26

pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not accessible")

pi.set_mode(GPIO_BUTTON, pigpio.INPUT)
pi.set_pull_up_down(GPIO_BUTTON, pigpio.PUD_OFF)
pi.set_glitch_filter(GPIO_BUTTON, 3000)  # Bounce time: 3000 µs = 3 ms

cb: pigpio._callback = pi.callback(GPIO_BUTTON, pigpio.EITHER_EDGE, button_callback)

print("Wait for keystrokes (Ctrl+C to exit)")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    cb.cancel()
    pi.stop()
