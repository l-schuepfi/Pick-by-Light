"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to communicate with an arduino via USB connection.
    Therefore, the Pi is simply connected with the arduino via USB.

    The program sends seven requests to the arduino and prints the response.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

import serial

ser: serial.Serial = serial.Serial("/dev/ttyACM0", 9600, timeout=2)
time.sleep(2)

line: str = ""
for i in range(7):
    print(f"Send request {i + 1}...")
    ser.write(b"R\n")

    # readline() waits up to 2 seconds for a response
    line = ser.readline().decode("utf-8").strip()

    if line:
        print(f"Response from Arduino: {line}")
    else:
        print("Error: Timeout - no response received.")

    time.sleep(0.1)

ser.close()
