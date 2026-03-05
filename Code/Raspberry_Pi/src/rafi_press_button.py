"""

    Pick-by-Light System
    -------------------------------------------------------------------
    Class to read events from the RAFI push button.
    Each change of the output of the push button leads to an interrupt.
    Within this interrupt, the event can be stored in a deque.
    From there, the application can retreive these events later on.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time
from multiprocessing.queues import Queue as mpQueue

import pigpio


class RAFI_Push_Button:
    def __init__(
        self, push_button_queue: mpQueue, gpio_pin: int = 26, pi: pigpio.pi | None = None
    ) -> None:
        if gpio_pin < 0 or gpio_pin > 27:
            raise ValueError("Pin must be between 0 and 27.")

        self.pi: pigpio.pi = pi if pi else pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio daemon not accessible")

        self.event_queue: mpQueue = push_button_queue

        self.pi.set_mode(gpio_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(gpio_pin, pigpio.PUD_OFF)
        self.pi.set_glitch_filter(gpio_pin, 3000)  # Bounce time: 3000 µs = 3 ms

        self.cb: pigpio._callback = self.pi.callback(
            gpio_pin, pigpio.EITHER_EDGE, self.button_callback
        )

    def button_callback(self, gpio: int, level: int, tick: int) -> None:
        # print(time.monotonic())
        # print("Button callback")
        self.event_queue.put((level, time.monotonic()))

    def close_connection(self) -> None:
        self.cb.cancel()
