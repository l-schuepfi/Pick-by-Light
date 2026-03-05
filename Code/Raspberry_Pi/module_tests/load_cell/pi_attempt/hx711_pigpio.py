"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Test class for Raspberry Pi to control a load cell outputs directly on the pi.
    The code is based on https://github.com/tatobari/hx711py,
    using pigpio instead of RPi.GPIO.

    Allows, among other things, taring and calibrations.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import threading
import time

import pigpio


class HX711:
    def __init__(self, dout: int, pd_sck: int, gain: int = 128, pi: pigpio.pi | None = None):
        self.PD_SCK: int = pd_sck
        self.DOUT: int = dout

        # Mutex for reading from the HX711, in case multiple threads in client
        # software try to access get values from the class at the same time.
        self.readLock: threading.Lock = threading.Lock()

        self.pi: pigpio.pi = pi if pi else pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio daemon not running")

        self.pi.set_mode(self.PD_SCK, pigpio.OUTPUT)
        self.pi.set_mode(self.DOUT, pigpio.INPUT)
        self.pi.write(self.PD_SCK, 0)

        self.GAIN: int = 0

        self.REFERENCE_UNIT: int = 1
        self.REFERENCE_UNIT_B: int = 1

        self.OFFSET: int | float = 1
        self.OFFSET_B: int | float = 1
        self.lastVal: int = 0

        self.DEBUG_PRINTING: int = False

        self.byte_format: str = "MSB"
        self.bit_format: str = "MSB"

        self.set_gain(gain)
        time.sleep(1)

    # ---------- Low level helpers ----------

    def convert_from_twos_complement_24_bit(self, value: int) -> int:
        return -(value & 0x800000) + (value & 0x7FFFFF)

    def is_ready(self) -> bool:
        return self.pi.read(self.DOUT) == 0

    def set_gain(self, gain: int):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        else:
            raise ValueError("Invalid gain value")

        self.pi.write(self.PD_SCK, 0)
        self.readRawBytes()  # dummy read

    def get_gain(self) -> int:
        return {1: 128, 3: 64, 2: 32}.get(self.GAIN, 0)

    def readNextBit(self) -> int:
        self.pi.write(self.PD_SCK, 1)
        self.pi.write(self.PD_SCK, 0)
        return int(self.pi.read(self.DOUT))

    def readNextByte(self) -> int:
        byteValue: int = 0

        for _ in range(8):
            if self.bit_format == "MSB":
                byteValue <<= 1
                byteValue |= self.readNextBit()
            else:
                byteValue >>= 1
                byteValue |= self.readNextBit() << 7

        return byteValue

    def readRawBytes(self) -> list[int]:
        self.readLock.acquire()

        try:
            while not self.is_ready():
                # pigpio.delay(10)
                pass

            first: int = self.readNextByte()
            second: int = self.readNextByte()
            third: int = self.readNextByte()

            for _ in range(self.GAIN):
                self.readNextBit()

            if self.byte_format == "LSB":
                return [third, second, first]
            else:
                return [first, second, third]

        finally:
            self.readLock.release()

    # ---------- High level read ----------

    def read_long(self) -> int:
        dataBytes: list[int] = self.readRawBytes()

        if self.DEBUG_PRINTING:
            print(dataBytes)

        value: int = (dataBytes[0] << 16) | (dataBytes[1] << 8) | dataBytes[2]

        signed: int = self.convert_from_twos_complement_24_bit(value)
        self.lastVal = signed
        return int(signed)

    def read_average(self, times: int = 3) -> int | float:
        if times <= 0:
            raise ValueError("times must be >= 1")

        if times == 1:
            return self.read_long()

        if times < 5:
            return self.read_median(times)

        values: list[int] = [self.read_long() for _ in range(times)]
        values.sort()

        trim: int = int(len(values) * 0.2)
        values = values[trim:-trim]

        return sum(values) / len(values)

    def read_median(self, times: int = 3) -> int | float:
        if times <= 0:
            raise ValueError("times must be > 0")

        values: list[int] = [self.read_long() for _ in range(times)]
        values.sort()

        mid: int = len(values) // 2
        if times & 1:
            return values[mid]
        else:
            return (values[mid - 1] + values[mid]) / 2.0

    # ---------- Channel A / B ----------

    def get_value(self, times: int = 3) -> int | float:
        return self.get_value_A(times)

    def get_value_A(self, times: int = 3) -> int | float:
        return self.read_median(times) - self.OFFSET

    def get_value_B(self, times: int = 3) -> int | float:
        g: int = self.get_gain()
        self.set_gain(32)
        value: int | float = self.read_median(times) - self.OFFSET_B
        self.set_gain(g)
        return value

    def get_weight(self, times: int = 3) -> float:
        return self.get_weight_A(times)

    def get_weight_A(self, times: int = 3) -> float:
        return self.get_value_A(times) / self.REFERENCE_UNIT

    def get_weight_B(self, times: int = 3) -> float:
        return self.get_value_B(times) / self.REFERENCE_UNIT_B

    # ---------- Tare ----------

    def tare(self, times: int = 15) -> int | float:
        return self.tare_A(times)

    def tare_A(self, times: int = 15) -> int | float:
        backup: int = self.REFERENCE_UNIT
        self.REFERENCE_UNIT = 1
        value: int | float = self.read_average(times)
        self.OFFSET = value
        self.REFERENCE_UNIT = backup
        return value

    def tare_B(self, times: int = 15) -> int | float:
        backupRef: int = self.REFERENCE_UNIT_B
        backupGain: int = self.get_gain()

        self.REFERENCE_UNIT_B = 1
        self.set_gain(32)

        value: int | float = self.read_average(times)
        self.OFFSET_B = value

        self.set_gain(backupGain)
        self.REFERENCE_UNIT_B = backupRef
        return value

    # ---------- Config ----------

    def set_reading_format(self, byte_format: str = "LSB", bit_format: str = "MSB") -> None:
        if byte_format not in ("LSB", "MSB"):
            raise ValueError("Invalid byte_format")
        if bit_format not in ("LSB", "MSB"):
            raise ValueError("Invalid bit_format")

        self.byte_format = byte_format
        self.bit_format = bit_format

    def set_reference_unit(self, value: int) -> None:
        self.REFERENCE_UNIT = value

    def set_reference_unit_B(self, value: int) -> None:
        self.REFERENCE_UNIT_B = value

    # ---------- Power ----------

    def power_down(self) -> None:
        self.readLock.acquire()
        try:
            self.pi.write(self.PD_SCK, 0)
            self.pi.write(self.PD_SCK, 1)
            time.sleep(0.0001)
        finally:
            self.readLock.release()

    def power_up(self) -> None:
        self.readLock.acquire()
        try:
            self.pi.write(self.PD_SCK, 0)
            time.sleep(0.0001)
        finally:
            self.readLock.release()

        if self.get_gain() != 128:
            self.readRawBytes()

    def reset(self) -> None:
        self.power_down()
        self.power_up()

    # ---------- pigpio Event Callback ----------

    def add_event_detect(self, callback):
        return self.pi.callback(self.DOUT, pigpio.FALLING_EDGE, callback)
