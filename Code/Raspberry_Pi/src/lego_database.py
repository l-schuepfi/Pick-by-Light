"""

    Pick-by-Light System
    -------------------------------------------------------------------
    Offers a function to convert an excel file into a dict containing
    all data for the display on the GUI. Each sheet is read separately,
    cells are checked for numerical values line by line. Numerical
    values are stored in a matrix (list of lines), cells without
    numbers are kept as `None`.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import os
from datetime import datetime as dt

import openpyxl


def _is_number(value: float | int | str | dt | bool | None) -> bool:
    """
    Checks whether 'value' can be interpreted as a number.
    Boolean values are excluded (since bool is a subclass of int in Python).
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, dt):
        return False
    try:
        # accepts ints, floats, and numeric strings
        float(value)
        return True
    except Exception:
        return False


def read_excel_matrices(path: str) -> dict[str, dict[str, list[list[dict[str, float | str]]]]]:
    """
    Loads the Excel file and returns a dict:

    key: sheet name (str)
    value: matrix as a list of rows; each cell is `float` or `None`.

    Searches rows containing at least one numeric cell.
    These are the lines containing the amount of components for a vehicle.
    From that, it collects the information from the lines above (weight, id, name).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    wb: openpyxl.workbook.workbook.Workbook = openpyxl.load_workbook(path, data_only=True)
    result: dict[str, dict[str, list[list[dict[str, float | str]]]]] = {}

    excel_row_idx: int = 0
    counter: int = 0
    amount_row: bool = False

    for sheet in wb.worksheets:
        matrix: dict[str, list[list[dict[str, float | str]]]] = {}
        orientation: str = "Unknown"
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
            # Check whether the line contains at least one number.
            excel_row_idx = row_idx + 1
            counter = 0
            amount_row = False
            for cell in row:
                if _is_number(cell):
                    counter += 1
                elif isinstance(cell, str) and cell.strip().lower() == "anzahl":
                    amount_row = True
                elif isinstance(cell, str) and cell.strip().lower() == "linke seite":
                    orientation = "Left_Side"
                elif isinstance(cell, str) and cell.strip().lower() == "rechte seite":
                    orientation = "Right_Side"
            if orientation == "Unknwon" or amount_row is False or counter <= 0 or counter % 7 != 0:
                continue

            processed_row: list[dict[str, float | str]] = []
            for col_idx, cell in enumerate(row):
                if _is_number(cell):
                    id = sheet[excel_row_idx - 2][col_idx].value
                    weight = sheet[excel_row_idx - 1][col_idx].value
                    processed_row.append(
                        {
                            "name": str(sheet[excel_row_idx - 3][col_idx - 2].value),
                            "id": str(id),
                            "weight": float(weight),
                            "amount": float(cell),
                        }
                    )
            if matrix.keys().__contains__(orientation) is False:
                matrix[orientation] = []
            matrix[orientation].append(processed_row)

        result[sheet.title] = matrix

    return result
