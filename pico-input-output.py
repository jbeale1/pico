# Read an input pin and turn onboard LED on when the input is high.
# code for Raspberry Pi Pico   J.Beale 7-March-2021

from machine import Pin  # for access to GPIO

led = Pin(25, Pin.OUT)                # set pin 25 (driving onboard LED) to output
button = Pin(16, Pin.IN, Pin.PULL_UP) # use pin 16 as input for a button going to ground

while True:
    if button.value():  # is input high?
        led.on()        # if so, turn LED on
    else:
        led.off()       # otherwise turn it off


# See also: https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/6
