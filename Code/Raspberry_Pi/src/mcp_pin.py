"""

    Pick-by-Light System
    -----------------------------------------------------------------------------------
    Class to calibrate, store calibration data and detect changes for each IR module.
    The first X values are used as calibration values, border values are excluded for
    the calculation of mean value and standard deviation. After calibration, new values
    can be analyzed. Within +- 6 standard deviations, these values are seen as normal.
    Outside these boders, the value is seen as change. Changes represent a person
    picking into the corresponding box.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import math

AMOUNT_CALIBRATION_VALUES = 14
AMOUNT_LOWER_EXCLUSION_VALUES = 2
AMOUNT_UPPER_EXCLUSION_VALUES = 2


class MCP_Pin:
    def __init__(self) -> None:
        self.start_low: float | None = None
        self.low_time_ms: float = 0.0

        self.calibration_samples: list[float] = [0.0] * AMOUNT_CALIBRATION_VALUES
        self.counter_calibration_samples: int = 0

        self.mean_value: float = 0.0
        self.stddev_value: float = 0.0
        self.upper_bound: float = 0.0

        self.last_evaluation_result: bool = True

    def is_calibration_finished(self) -> bool:
        """
        Returns true if enough calibration values have been collected, otherwise false.
        """
        return self.counter_calibration_samples >= AMOUNT_CALIBRATION_VALUES

    def add_calibration_value(self) -> bool:
        """
        Adds the passed value to the calibration values.
        Returns true if enough calibration values have been collected, including this value.
        """
        if self.counter_calibration_samples < AMOUNT_CALIBRATION_VALUES and self.low_time_ms > 5.0:
            self.calibration_samples[self.counter_calibration_samples] = self.low_time_ms
            self.counter_calibration_samples += 1

            if self.counter_calibration_samples == AMOUNT_CALIBRATION_VALUES:
                self._calculate_and_store_lower_and_upper_bounds()

        return self.counter_calibration_samples >= AMOUNT_CALIBRATION_VALUES

    def _calculate_and_store_mean_calibration_value(self) -> float:
        """
        Calculates the mean value of the calibration values.
        Ignores values before the start index or after the end index.
        Returns the calculated value.
        """
        arr: list[float] = sorted(self.calibration_samples)
        start: int = AMOUNT_LOWER_EXCLUSION_VALUES  # ignore smallest values (outliers)
        end: int = (
            AMOUNT_CALIBRATION_VALUES - 1 - AMOUNT_UPPER_EXCLUSION_VALUES
        )  # ignore largest values (outliers)

        relevant: list[float] = arr[start : end + 1]
        self.mean_value = sum(relevant) / len(relevant)
        return self.mean_value

    def _calculate_and_store_standard_deviation_calibration_value(self) -> float:
        """
        Calculates the standard deviation of the calibration values.
        Ignores values before the start index or after the end index.
        Returns the calculated value.
        """
        self._calculate_and_store_mean_calibration_value()

        arr: list[float] = sorted(self.calibration_samples)
        start: int = AMOUNT_LOWER_EXCLUSION_VALUES  # ignore smallest values (outliers)
        end: int = (
            AMOUNT_CALIBRATION_VALUES - 1 - AMOUNT_UPPER_EXCLUSION_VALUES
        )  # ignore largest values (outliers)

        relevant: list[float] = arr[start : end + 1]
        mean: float = self.mean_value

        self.stddev_value = math.sqrt(sum((x - mean) ** 2 for x in relevant) / len(relevant))
        return self.stddev_value

    def _calculate_and_store_lower_and_upper_bounds(self) -> None:
        self._calculate_and_store_standard_deviation_calibration_value()
        self.upper_bound = max(80.0, min(100.0, self.mean_value * 1.5))

    def evaluate_measured_low_time(self, only_new_handles: bool = False) -> tuple[bool, bool]:
        """
        Return value 1: Is measured low time normal?
        Return value 2: Is a handle finished?
        """

        if self.counter_calibration_samples >= AMOUNT_CALIBRATION_VALUES:
            if self.low_time_ms <= self.upper_bound:
                if self.last_evaluation_result is False:
                    self.last_evaluation_result = True
                    return (True, True)
                return (True, False)
            else:
                # print(f"{self.low_time_ms} > {self.upper_bound}")
                if only_new_handles is True and self.last_evaluation_result is False:
                    return (True, False)
                else:
                    self.last_evaluation_result = False
                    return (False, False)
        else:
            self.add_calibration_value()
            return (True, False)

    def test_evaluate_measured_low_time(
        self, mcp_idx: int, pin_idx: int, print_mcp_idx: int, print_pin_idx: int
    ) -> bool:
        if self.counter_calibration_samples >= AMOUNT_CALIBRATION_VALUES:
            if self.low_time_ms <= self.upper_bound:
                if mcp_idx == print_mcp_idx and pin_idx == print_pin_idx:
                    print(
                        f"Nichts erkannt an MCP {mcp_idx}, Pin {pin_idx}"
                        + f" ({self.low_time_ms} < {self.upper_bound})"
                    )
                return True
            else:
                if mcp_idx == print_mcp_idx and pin_idx == print_pin_idx:
                    print(
                        f"Eingriff an MCP {mcp_idx}, Pin {pin_idx} !!!"
                        + f" ({self.low_time_ms} > {self.upper_bound})"
                    )
                return False
        else:
            self.add_calibration_value()
            return True

    def print_calibration_value(self, mcp_idx: int, pin_idx: int) -> None:
        # if self.mean_value >= 80.0:
        print(
            f"MCP {mcp_idx} - Pin {pin_idx} - Mean: {self.mean_value}"
            + f" - Std_dev: {self.stddev_value}"
        )
