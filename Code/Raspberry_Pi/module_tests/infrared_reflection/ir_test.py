"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to check if a IR-module is working.
    A module consists of an IR diode (IR7373C) and an IR receiver (TSSP4P38),
    which are optically separated so that a signal can only be received via reflection.

    The circuit shown in 'setup_ir_test.pdf' was set up for this test.

    The test continuously sends a pulsed signal with 38kHz and a duty cylce of 1.5%.
    It detects the duration of the LOW signal at the receiver output and displays it.
    To reduce the receiver's amplification again, a pause of 380 ms is inserted after
    each 120 ms transmission time. The program ends when pressing Ctrl + C.

    Author: Andreas Katzenberger
    Date: 2026-02-26

"""

import time

import pigpio


def get_low_time_ms() -> float:
    """
    Measures the duration of the LOW signal
    """
    start_low: float = 0.0
    end_low: float = 0.0

    while True:
        # Waiting for falling edge (receiver detects signal)
        while pi.read(RECEIVER_PIN) == 1:
            time.sleep(0.0001)

        start_low = time.time()

        # Waiting for rising edge (signal lost)
        while pi.read(RECEIVER_PIN) == 0:
            time.sleep(0.0001)

        end_low = time.time()
        return (end_low - start_low) * 1000.0


# Configuration
IR_LED_PIN = 12  # Hardware PWM0 (GPIO12)
RECEIVER_PIN = 24  # GPIO 24

# Time constants (in seconds)
BURST_TIME = 0.120  # Send for 120ms
CYCLE_TIME = 0.500  # 500ms total cycle
PAUSE_TIME = CYCLE_TIME - BURST_TIME

FREQUENCY = 38000
DUTY_CYCLE = 15000  # 1.5% from 1.000.000

pi: pigpio.pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio daemon not accessible")

pi.set_mode(RECEIVER_PIN, pigpio.INPUT)
pi.set_pull_up_down(RECEIVER_PIN, pigpio.PUD_UP)

try:
    print("System ready. 38kHz high-power carrier active.")

    start_burst: float = 0.0
    low_ms: float = 0.0

    while True:
        # 1. Start burst (hardware PWM)
        pi.hardware_PWM(IR_LED_PIN, FREQUENCY, DUTY_CYCLE)
        start_burst = time.time()

        # During the burst, we can measure (or execute the logic)
        # Note: Since we do not have real interrupts here as with the AVR,
        #       let's just measure once per burst.
        low_ms = get_low_time_ms()
        print(f"Recognized: {low_ms:.2f} ms")

        # Wait until 120ms have passed
        while (time.time() - start_burst) < BURST_TIME:
            time.sleep(0.005)

        # 2. Stop burst (pause)
        pi.hardware_PWM(IR_LED_PIN, FREQUENCY, 0)

        # Take a break
        time.sleep(PAUSE_TIME)

except KeyboardInterrupt:
    print("\nExit program...")
    pi.hardware_PWM(IR_LED_PIN, FREQUENCY, 0)
    pi.stop()
