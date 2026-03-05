"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to control IR diodes
    and read the IR receiver output of a whole row.

    The circuit shown in 'setup_mcp_ir_test.pdf' was set up for this test.

    This program controls the IR diodes via a transistor circuit and the power supply
    (to obtain a pulsed 5V signal.). Each module consists of an IR diode (IR7373C)
    and an IR receiver (TSSP4P38), which are optically separated so that a signal can
    only be received via reflection. The test continuously sends a pulsed signal with
    38kHz and a duty cylce of 1.5%. To reduce the receiver's amplification again, a
    pause of 380 ms is inserted after each 120 ms transmission time.

    The program uses the interrupt registers to perform a targeted readout when changes
    are made to the GPIOs. The two registers are mirrored so that all changes can be
    registered via a pin. As soon as there is a change in the interrupt level, all GPIO
    states are queried via I2C and the respective LOW times are determined and output.
    The program ends when pressing Ctrl + C.

    Author: Andreas Katzenberger
    Date: 2026-02-26

"""

import threading
import time

import pigpio


# Interrupt Callback (mark ONLY!)
def mcp_interrupt(gpio: int, level: int, tick: int) -> None:
    global irq_lock, irq_pending, irq_tick
    with irq_lock:
        irq_pending = True
        irq_tick = tick


# Reading MCP with retry
def read_mcp_state() -> int | None:
    porta: int = 0
    portb: int = 0

    for _ in range(3):
        try:
            porta = pi.i2c_read_byte_data(h, GPIOA)
            portb = pi.i2c_read_byte_data(h, GPIOB)
            return porta | (portb << 8)
        except pigpio.error:
            time.sleep(0.001)
    return None


# pigpio Init
pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not accessible")

I2C_BUS = 1
MCP_ADDR = 0x20

# Register
IODIRA = 0x00
IODIRB = 0x01
GPPUA = 0x0C
GPPUB = 0x0D
GPINTENA = 0x04
GPINTENB = 0x05
INTCONA = 0x08
INTCONB = 0x09
GPIOA = 0x12
GPIOB = 0x13

INT_GPIO = 4

h: int = pi.i2c_open(I2C_BUS, MCP_ADDR)

# All pins input
pi.i2c_write_byte_data(h, IODIRA, 0xFF)
pi.i2c_write_byte_data(h, IODIRB, 0xFF)

# Pull-ups on
pi.i2c_write_byte_data(h, GPPUA, 0xFF)
pi.i2c_write_byte_data(h, GPPUB, 0xFF)

# Interrupt on every change
pi.i2c_write_byte_data(h, INTCONA, 0x00)
pi.i2c_write_byte_data(h, INTCONB, 0x00)

# Enable interrupts
pi.i2c_write_byte_data(h, GPINTENA, 0xFF)
pi.i2c_write_byte_data(h, GPINTENB, 0xFF)

# IOCON: Mirror INTA & INTB (both registers!)
pi.i2c_write_byte_data(h, 0x0A, 0b01000000)
pi.i2c_write_byte_data(h, 0x0B, 0b01000000)

# Acknowledge interrupt (if already present at start)
pi.i2c_read_byte_data(h, GPIOA)
pi.i2c_read_byte_data(h, GPIOB)

# Status management MCP
low_start: list[int | None] = [None] * 16
last_state: int = 0xFFFF

irq_pending: bool = False
irq_tick: int = 0
irq_lock: threading.Lock = threading.Lock()

# INT GPIO Setup
pi.set_mode(INT_GPIO, pigpio.INPUT)
pi.set_pull_up_down(INT_GPIO, pigpio.PUD_UP)
cb: pigpio._callback = pi.callback(INT_GPIO, pigpio.FALLING_EDGE, mcp_interrupt)

last_pending_irq: float = time.monotonic()
tick = 0.0
state: int | None = None
changed: int = 0
mask: int = 0
duration: float = 0.0

# IR / 38kHz burst configuration
IR_LED_PIN = 13
FREQUENCY = 38000
DUTY_CYCLE = 15000  # 1.5 %

BURST_TIME = 0.120
CYCLE_TIME = 0.500
PAUSE_TIME = CYCLE_TIME - BURST_TIME

ir_on: bool = False
ir_next_toggle: float = time.monotonic()
now: float = 0.0

# Main Loop
try:
    print("System active – Non-blocking-architecture")

    while True:
        now = time.monotonic()

        # IR state machine (non-blocking)
        if not ir_on and now >= ir_next_toggle:
            pi.hardware_PWM(IR_LED_PIN, FREQUENCY, DUTY_CYCLE)
            ir_on = True
            ir_next_toggle = now + BURST_TIME

        elif ir_on and now >= ir_next_toggle:
            pi.hardware_PWM(IR_LED_PIN, FREQUENCY, 0)
            ir_on = False
            ir_next_toggle = now + PAUSE_TIME

        # MCP interrupt evaluation
        with irq_lock:
            if not irq_pending and time.monotonic() - last_pending_irq < 0.50:
                time.sleep(0.001)
                continue
            irq_pending = False
            tick = irq_tick

        last_pending_irq = time.monotonic()

        state = read_mcp_state()
        if state is None:
            continue

        changed = last_state ^ state

        for pin in range(16):
            mask = 1 << pin
            if not (changed & mask):
                continue

            if not (state & mask):
                low_start[pin] = int(tick)
            else:
                if low_start[pin] is not None:
                    duration = pigpio.tickDiff(low_start[pin], tick) / 1000
                    print(f"MCP Pin {pin:02d} LOW for {duration:.2f} ms")
                    low_start[pin] = None

        last_state = state

except KeyboardInterrupt:
    print("\nFinished")

finally:
    pi.hardware_PWM(IR_LED_PIN, FREQUENCY, 0)
    cb.cancel()
    pi.i2c_close(h)
    pi.stop()
