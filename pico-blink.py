# Blink the LED on the Pico board
# https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/5

from machine import Pin, Timer
led = Pin(25, Pin.OUT)
timer = Timer()

def blink(timer):
    led.toggle()

timer.init(freq=2.5, mode=Timer.PERIODIC, callback=blink)
