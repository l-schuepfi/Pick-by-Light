"""

    Pick-by-Light System
    -----------------------------------------------
    Class to control WS2812B LED strips.
    Extends the neopixel class from Adafruit.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import board
import neopixel
from adafruit_blinka.microcontroller.generic_linux.rpi_gpio_pin import Pin


class RGB_Color:
    def __init__(self, red: int = 0, green: int = 0, blue: int = 0) -> None:
        if red < 0 or red > 255:
            raise ValueError("Red must be between 0 and 255.")
        if green < 0 or green > 255:
            raise ValueError("Green must be between 0 and 255.")
        if blue < 0 or blue > 255:
            raise ValueError("Blue must be between 0 and 255.")

        self.r = red
        self.g = green
        self.b = blue

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)


class WS2812B:
    def __init__(
        self,
        gpio_pin: Pin = board.D13,
        led_count: int = 10,
        brightness: float = 1.0,
        auto_write: bool = False,
        order: str = neopixel.GRB,
    ) -> None:
        """
        Use hardware PWM Pins for controlling the strips.
        Up to two strips can be controlled simultaneously.
        Use GPIO13/GPIO19 and GPIO12/GPIO18 for this purpose.
        """
        if led_count < 1:
            raise ValueError("led_count must be at least 1.")
        if brightness > 1.0 or brightness < 0.0:
            raise ValueError("Brightness must be between 0.0 and 1.0.")

        self.led_count: int = led_count
        self.pixels: neopixel.NeoPixel = neopixel.NeoPixel(
            gpio_pin,
            led_count,
            brightness=brightness,  # 0.0 to 1.0
            auto_write=auto_write,  # Only update when the .show() command is executed
            pixel_order=order,
        )

    def light_up(self, indices: list[tuple[int, RGB_Color]]) -> None:
        self.pixels.fill((0, 0, 0))
        for index in indices:
            if 0 <= index[0] < self.led_count:
                self.pixels[index[0]] = index[1].to_tuple()
        self.pixels.show()

    def light_up_all(self, color: RGB_Color) -> None:
        self.pixels.fill((0, 0, 0))
        for index in range(self.led_count):
            self.pixels[index] = color.to_tuple()
        self.pixels.show()

    def turn_off(self) -> None:
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
