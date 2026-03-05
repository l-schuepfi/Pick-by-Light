"""

    Pick-by-Light System
    --------------------------------------------------------
    Collection of strings used as output in the application.
    This should enable an easy switch between languages.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

# flake8: noqa

texts: dict[str, dict[str, str]] = {
    "de": {
        "title": "Bauteil-Viewer",
        "heading": "Pick-by-Light",
        "calibration_hint": "Kalibrierung läuft ...",
        "content_rfid_hint": "Schiebe deine Kiste in die Halterung",
        "status_rfid": "Kiste scannen ...",
        "from": "von",
        "left_side": "Linke Seite",
        "right_side": "Rechte Seite",
        "content_new_vehicle": "Entferne deine Kiste und schiebe eine neue in die Halterung ein",
        "status_new_vehicle": "Kiste tauschen ...",
        "content_canceled": "Schiebe eine neue Kiste in die Halterung ein",
        "status_canceled": "Abbruch ...",
        "content_lc_calibration": "Kalibrierung der Waage",
        "status_lc_calib_start": "Kalibrierung der Waage wird gestartet ...",
        "status_lc_taring": "Leere die Waage und drücke dann den Taster ...",
        "status_lc_calib_weight": "Lege nun Gewichte (200g) in die Waage und drücke dann den Taster ...",
        "stauts_lc_sec_taring": "Leere die Waage nochmals und drücke dann den Taster ...",
        "status_lc_calib_finished": "Kalibirierung der Waage abgeschlossen.",
        "status_error_acknowledged": "Fehler behoben. Du kannst fortfahren.",
        "status_take_item": "Nehme Teile aus der beleuchteten Kiste ...",
        "status_correct_module": "Lege die entnommenen Teile in die Waage ...",
        "status_wrong_module": "Falsche Kiste! Betätige den Taster nach Behebung des Fehlers um fortzufahren ...",
        "status_correct_weight": "Menge OK! Nächstes Teil.",
        "status_all_picked": "Genug Eingriffe. Nächstes Teil ...",
        "status_some_picked": "Eingriff erkannt. 2 Teile abgezogen ...",
        "status_some_weight_1": "neues Teil erkannt ...",
        "status_some_weight": "neue Teile erkannt ...",
        "status_too_much_weight": "Zu viele Teile! Betätige den Taster nach Behebung des Fehlers um fortzufahren ...",
        "manual_next_item": "Manuell zum nächsten Teil gewechselt ...",
        "manual_previous_item": "Manuell zum vorherigen Teil gewechselt ...",
        "pigpio_not_connected": "pigpio-Daemon nicht verbunden. Führe 'sudo pigpiod' aus.",
    },
    "en": {
        "title": "Component-Viewer",
        "heading": "Pick-by-Light",
        "calibration_hint": "Calibration in progress...",
        "content_rfid_hint": "Push your box into the holder",
        "status_rfid": "Scan box ...",
        "from": "from",
        "left_side": "Left side",
        "right_side": "Right side",
        "content_new_vehicle": "Remove your box and insert a new one into the holder",
        "status_new_vehicle": "Swap boxes ...",
        "content_canceled": "Insert a new box into the holder",
        "status_canceled": "Canceled ...",
        "content_lc_calibration": "Calibration of the scale",
        "status_lc_calib_start": "Calibration of the scale is starting ...",
        "status_lc_taring": "Empty the scale and then press the button ...",
        "status_lc_calib_weight": "Now place weights (200g) on the scale and then press the button ...",
        "stauts_lc_sec_taring": "Empty the scale again and then press the button ...",
        "status_lc_calib_finished": "Calibration of the scale completed.",
        "status_error_acknowledged": "Error fixed. You can continue.",
        "status_correct_module": "Place the removed parts on the scale ...",
        "status_wrong_module": "Wrong box! Press the button after correcting the error to continue ...",
        "status_take_item": "Take items from the illuminated box ...",
        "status_correct_weight": "Quantity OK! Next item.",
        "status_all_picked": "Enough interventions. Next item ...",
        "status_some_picked": "Intervention detected. 2 parts subtracted ...",
        "status_some_weight_1": "new item recognized ...",
        "status_some_weight": "new items recognized ...",
        "status_too_much_weight": "Too many parts! Press the button after correcting the error to continue ...",
        "manual_next_item": "Changed manually to the next item ...",
        "manual_previous_item": "Changed manually to the previous item ...",
        "pigpio_not_connected": "pigpio-Daemon not connected. Execute 'sudo pigpiod'.",
    },
}
