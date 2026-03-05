"""

    Pick-by-Light System
    -----------------------------------------------
    Class to read RFID tags from the RC522 module.
    Offers functions to easily retreive RFID tags
    when holding them in front of the RC522 module.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import time

from mfrc522 import MFRC522


class RFIDReader:
    def __init__(self) -> None:
        self.reader: MFRC522 = MFRC522()
        self.reader.MFRC522_Init()

    def poll_tag(self) -> list[int] | None:
        status: int = 0
        uid: list[int] = []

        status, _ = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
        if status == self.reader.MI_OK:
            status, uid = self.reader.MFRC522_Anticoll()
            if status == self.reader.MI_OK:
                return uid
        return None

    def read_tag(self, blocking: bool = True) -> list[int] | None:
        if blocking:
            try:
                while True:
                    uid = self.poll_tag()
                    if uid is not None:
                        return uid
                    time.sleep(0.1)
            finally:
                pass
        else:
            return self.poll_tag()
