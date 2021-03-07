# Watch an input pin and measure elapsed time between rising edges
# basic example using only Python, not the PIO state machine hardware
# Raspberry Pi Pico   J.Beale 7-March-2021

from machine import Pin  # for access to GPIO
import time  # for elapsed time

led = Pin(25, Pin.OUT)                # set pin 25 (driving onboard LED) to output
button = Pin(16, Pin.IN, Pin.PULL_UP) # use pin 16 as input for a button going to ground

tus = time.ticks_us   # Timer object with 1 MHz timer, so value is in microseconds
tOld = tus()          # get initial count of microseconds
bOld = button.value() # get initial input level

while True:
    bNew = button.value()  # read new input level
    if bNew != bOld:       # did input level change?
        if bNew:
            tNew = tus()    # get the timer value now
            tDelta = tNew - tOld # elapsed microseconds        
            print(tDelta)
            led.on()        # signal high input with LED
            bOld = bNew         # remember this input level
            tOld = tNew         # remember this counter value
        else:
            led.off()       # signal low input with LED
