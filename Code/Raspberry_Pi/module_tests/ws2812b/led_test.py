"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to control two WS2812B LED strips.

    The circuit shown in 'setup_led_test.pdf' was set up for this test.

    First, a few LEDs are switched on selectively.
    Then a running light is started, which runs through the entire strip repeatedly.
    This allows you to check whether each individual LED on the strip is still working.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import board
import neopixel

# Configuration
LED_PIN_LARGE_STRIP = board.D12  # GPIO 12
LED_PIN_SHORT_STRIP = board.D13  # GPIO 13
LED_COUNT_LARGE_STRIP = 865  # Number of LEDs in the large strip
LED_COUNT_SHORT_STRIP = 15  # Number of LEDs in the short strip
ORDER = neopixel.GRB  # Color Sequence

# Initialization of the LED strips
pixels_long: neopixel.NeoPixel = neopixel.NeoPixel(
    LED_PIN_LARGE_STRIP,
    LED_COUNT_LARGE_STRIP,
    brightness=1.0,  # 0.0 to 1.0
    auto_write=False,  # Only update when the .show() command is executed
    pixel_order=ORDER,
)

pixels_short: neopixel.NeoPixel = neopixel.NeoPixel(
    LED_PIN_SHORT_STRIP,
    LED_COUNT_SHORT_STRIP,
    brightness=1.0,  # 0.0 to 1.0
    auto_write=False,  # Only update when the .show() command is executed
    pixel_order=ORDER,
)


def main():
    # Turn off all LEDs
    pixels_long.fill((0, 0, 0))
    pixels_short.fill((0, 0, 0))

    # Light up some LEDs, index starts at 0
    pixels_long[0] = (255, 0, 0)  # (Red, Green, Blue)
    pixels_short[0] = (255, 0, 0)  # (Red, Green, Blue)
    pixels_short[14] = (255, 0, 0)  # (Red, Green, Blue)

    pixels_long[122] = (255, 0, 0)  # (Red, Green, Blue)
    pixels_long[123] = (255, 0, 0)  # (Red, Green, Blue)
    pixels_long[124] = (255, 0, 0)  # (Red, Green, Blue)
    pixels_long[125] = (255, 0, 0)  # (Red, Green, Blue)

    # Send changes to the strips
    pixels_long.show()
    pixels_short.show()
    print("Die LEDs leuchten nun rot.")

    # Start running lights
    i: int = 0
    while True:
        pixels_long.fill((0, 0, 0))
        pixels_long[i % LED_COUNT_LARGE_STRIP] = (255, 0, 0)  # (Red, Green, Blue)
        pixels_long[(i + 1) % LED_COUNT_LARGE_STRIP] = (255, 0, 0)  # (Red, Green, Blue)
        pixels_long[(i + 2) % LED_COUNT_LARGE_STRIP] = (255, 0, 0)  # (Red, Green, Blue)
        pixels_long[(i + 3) % LED_COUNT_LARGE_STRIP] = (0, 255, 0)  # (Red, Green, Blue)
        pixels_long[(i + 4) % LED_COUNT_LARGE_STRIP] = (0, 255, 0)  # (Red, Green, Blue)
        pixels_long[(i + 5) % LED_COUNT_LARGE_STRIP] = (0, 255, 0)  # (Red, Green, Blue)
        pixels_long[(i + 6) % LED_COUNT_LARGE_STRIP] = (0, 0, 255)  # (Red, Green, Blue)
        pixels_long[(i + 7) % LED_COUNT_LARGE_STRIP] = (0, 0, 255)  # (Red, Green, Blue)
        pixels_long[(i + 8) % LED_COUNT_LARGE_STRIP] = (0, 0, 255)  # (Red, Green, Blue)
        i += 1
        if i >= LED_COUNT_LARGE_STRIP:
            i = 0
        pixels_long.show()
        time.sleep(0.01)


if __name__ == "__main__":
    try:
        main()
        exit(0)
    except KeyboardInterrupt:
        # All LEDs off when canceled
        pixels_long.fill((0, 0, 0))
        pixels_long.show()
        pixels_short.fill((0, 0, 0))
        pixels_short.show()
