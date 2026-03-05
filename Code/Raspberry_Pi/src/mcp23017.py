"""

    Pick-by-Light System
    ----------------------------------------------------------------------------------
    Class to communicate with the MCP23017 modules and to detect changes in each row.
    After calibration is finished, all handles in boxes connected with the MCP can be
    retrieved. For the communication with the MCP, interrupt based I2C calls are used.
    Values greater than 120ms are not used as they are not possible when only sending
    for 120ms.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import pigpio

from mcp_pin import MCP_Pin

# MCP23017 I2C register addresses
IODIRA = 0x00
IODIRB = 0x01
GPPUA = 0x0C
GPPUB = 0x0D
INTCONA = 0x08
INTCONB = 0x09
GPINTENA = 0x04
GPINTENB = 0x05
GPIOA = 0x12
GPIOB = 0x13


class MCP23017:
    def __init__(
        self,
        address_offset: int = 0,
        busnum: int = 1,
        int_gpio_pin: int = 17,
        pi: pigpio.pi | None = None,
    ):
        """
        Address = 0x20 + parameter
        Parameter = 0 → I2C address 0x20
        Parameter = 7 → I2C address 0x27
        """
        self.addr: int = 0x20 + address_offset

        self.mcp_last_state: int = 0xFFFF

        self.pi: pigpio.pi = pi if pi else pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio daemon not accessible")

        while True:
            try:
                self.i2c_handle: int = self.pi.i2c_open(busnum, self.addr)

                # All pins input
                self.pi.i2c_write_byte_data(self.i2c_handle, IODIRA, 0xFF)
                self.pi.i2c_write_byte_data(self.i2c_handle, IODIRB, 0xFF)

                # Pull-ups on
                self.pi.i2c_write_byte_data(self.i2c_handle, GPPUA, 0xFF)
                self.pi.i2c_write_byte_data(self.i2c_handle, GPPUB, 0xFF)

                # Interrupt on every change
                self.pi.i2c_write_byte_data(self.i2c_handle, INTCONA, 0x00)
                self.pi.i2c_write_byte_data(self.i2c_handle, INTCONB, 0x00)

                # Enable interrupts
                self.pi.i2c_write_byte_data(self.i2c_handle, GPINTENA, 0xFF)
                self.pi.i2c_write_byte_data(self.i2c_handle, GPINTENB, 0xFF)

                # IOCON: Mirror INTA & INTB (both registers!)
                self.pi.i2c_write_byte_data(self.i2c_handle, 0x0A, 0b01000000)
                self.pi.i2c_write_byte_data(self.i2c_handle, 0x0B, 0b01000000)
                break
            except pigpio.error:
                time.sleep(0.001)

        # INT GPIO Setup
        self.pi.set_mode(int_gpio_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(int_gpio_pin, pigpio.PUD_UP)

        self.pins: list[MCP_Pin] = [MCP_Pin() for _ in range(16)]
        self.last_pending_irq: float = time.monotonic()

        while True:
            try:
                # Acknowledge interrupt (if already present at start)
                self.pi.i2c_read_byte_data(self.i2c_handle, GPIOA)
                self.pi.i2c_read_byte_data(self.i2c_handle, GPIOB)
                break
            except pigpio.error:
                time.sleep(0.001)

    # Reading MCP with retry
    def read_mcp_state(self) -> int | None:
        porta: int = 0
        portb: int = 0

        for _ in range(3):
            try:
                porta = self.pi.i2c_read_byte_data(self.i2c_handle, GPIOA)
                portb = self.pi.i2c_read_byte_data(self.i2c_handle, GPIOB)
                return porta | (portb << 8)
            except pigpio.error:
                time.sleep(0.001)
        return None

    def update(self, only_new_handles: bool = False) -> list[int]:
        pins_with_handle: list[int] = []

        self.last_pending_irq = time.monotonic()
        tick: float = time.monotonic()

        state: int | None = self.read_mcp_state()
        if state is None:
            return pins_with_handle

        changed: int = self.mcp_last_state ^ state
        mask: int = 0
        duration: float = 0.0
        detection: bool = False
        handle_finished: bool = False

        for pin in range(16):
            if pin % 8 == 7:
                continue

            mask = 1 << pin
            if not (changed & mask):
                continue

            if not (state & mask):
                self.pins[pin].start_low = tick
            else:
                if self.pins[pin].start_low is not None:
                    duration = pigpio.tickDiff(self.pins[pin].start_low, tick) * 1000
                    if duration <= 120.0:
                        self.pins[pin].low_time_ms = duration
                        (detection, handle_finished) = self.pins[pin].evaluate_measured_low_time(
                            only_new_handles
                        )
                        if only_new_handles is True:
                            if handle_finished is True:
                                pins_with_handle.append(pin)
                        else:
                            if detection is False:
                                pins_with_handle.append(pin)
                        self.pins[pin].start_low = None

        self.mcp_last_state = state
        return pins_with_handle

    def test_update(self, mcp_idx: int, print_mcp_idx: int, print_pin_idx: int) -> list[int]:
        pins_with_handle: list[int] = []

        self.last_pending_irq = time.monotonic()
        tick: float = time.monotonic()

        state: int | None = self.read_mcp_state()
        if state is None:
            return pins_with_handle

        changed: int = self.mcp_last_state ^ state
        mask: int = 0
        duration: float = 0.0

        for pin in range(16):
            if pin % 8 == 7:
                continue

            mask = 1 << pin
            if not (changed & mask):
                continue

            if not (state & mask):
                self.pins[pin].start_low = tick
            else:
                if self.pins[pin].start_low is not None:
                    duration = pigpio.tickDiff(self.pins[pin].start_low, tick) * 1000
                    if duration <= 120.0:
                        self.pins[pin].low_time_ms = duration
                        if (
                            self.pins[pin].test_evaluate_measured_low_time(
                                mcp_idx, pin, print_mcp_idx, print_pin_idx
                            )
                            is False
                        ):
                            pins_with_handle.append(pin)
                        self.pins[pin].start_low = None

        self.mcp_last_state = state
        return pins_with_handle

    def is_calibration_finished(self) -> bool:
        finished_calibration_pins: int = 0
        all_finished: bool = True
        for idx, pin in enumerate(self.pins):
            if idx % 8 == 7:
                continue

            if pin.is_calibration_finished() is False:
                all_finished = False
            else:
                finished_calibration_pins += 1
        return all_finished

    def print_calibration_values(self, mcp_idx: int) -> None:
        for pin_idx, pin in enumerate(self.pins):
            if pin_idx % 8 == 7:
                continue
            pin.print_calibration_value(mcp_idx, pin_idx)
        print()

    def close_connection(self):
        self.pi.i2c_close(self.i2c_handle)
