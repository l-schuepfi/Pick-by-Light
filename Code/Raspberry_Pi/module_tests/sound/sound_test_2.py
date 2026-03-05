"""

    Pick-by-Light System
    --------------------------------------------------------------------------------
    Test for the sound module. Uses aplay and subprocess to play an error sound.
    Can be used to test if the sound module is working properly on the Raspberry Pi.
    Caution: When using the LED strips in parallel, the hardware timers for the
             audio signal are not available, which can cause problems.
    If no sound is output, reboot the Raspberry Pi and try the script again.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import subprocess
import time


def play_error_as_user() -> None:
    # system should run 'aplay' as User 'admin'
    # 'plughw:1,0' is our jack (Card 1)
    cmd: str = (
        "sudo -u admin aplay -D plughw:1,0 /home/admin/dev/Pick-by-Light/data/error_sound.wav"
    )
    subprocess.Popen(cmd, shell=True)


play_error_as_user()
time.sleep(5)
