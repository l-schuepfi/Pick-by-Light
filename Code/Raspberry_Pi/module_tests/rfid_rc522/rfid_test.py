"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test program for Raspberry Pi to read RFID tags from a RC522 module.

    The circuit shown in 'setup_rfid_test.pdf' was set up for this test.

    The test continuously checks whether an RFID tag is held in front of the sensor.
    As soon as a tag is detected, it outputs the corresponding UID and ends the test.

    Author: Andreas Katzenberger
    Date: 2026-02-26

"""

import time

from mfrc522 import MFRC522

reader: MFRC522 = MFRC522()
reader.MFRC522_Init()

status: int = 0
tag_type: int = 0
uid: list[str] = []

try:
    while True:
        status, tag_type = reader.MFRC522_Request(reader.PICC_REQIDL)

        if status == reader.MI_OK:
            status, uid = reader.MFRC522_Anticoll()
            if status == reader.MI_OK:
                print("UID:", uid)
                break

        time.sleep(0.1)
finally:
    pass
