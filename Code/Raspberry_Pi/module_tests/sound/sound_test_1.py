"""

    Pick-by-Light System
    --------------------------------------------------------------------------------
    Test for the sound module. Uses pygame to play an error sound.
    Can be used to test if the sound module is working properly on the Raspberry Pi.
    Caution: When using the LED strips in parallel, the hardware timers for the
             audio signal are not available, which can cause problems.
    If no sound is output, reboot the Raspberry Pi and try the script again.

    Author: Andreas Katzenberger
    Date: 2026-02-22

"""

import os
import time

import pygame

os.environ["SDL_AUDIODRIVER"] = "alsa"

pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)  # Optimize Buffer for Pi
pygame.mixer.init()
# pygame.mixer.music.load("data/error_sound.mp3")
# pygame.mixer.music.play()
# while pygame.mixer.music.get_busy():
#     time.sleep(0.1)

error_sound: pygame.mixer.Sound = pygame.mixer.Sound("data/error_sound.mp3")
error_sound.play()
time.sleep(2)
