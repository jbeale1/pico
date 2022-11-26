# test Pi Pico W PWM function
# J.Beale 22-Nov-2022

from machine import Pin, PWM
from time import sleep

dtime = 0.004  # PWM update delay time in seconds
step = 25      # PWM 16-bit increment per cycle

p1 = PWM(Pin(12))
p2 = PWM(Pin(13))
p1.freq(1000)
p2.freq(1000)
p1.duty_u16(0)
p2.duty_u16(0)

led = machine.Pin('LED', machine.Pin.OUT)
for i in range(4):
    led.on()
    sleep(0.25)
    led.off()
    sleep(0.25)


while True:
    p1.duty_u16(0)
    p2.duty_u16(0)
    led.off()
    for duty in range(0,65535,step):
        p1.duty_u16(duty)
        sleep(dtime)

    led.on()
    for i in range(0,65535,step):
        duty = 65535-i
        p1.duty_u16(duty)
        sleep(dtime)
        
    led.off()
    p1.duty_u16(0)
    for duty in range(0,65535,step):
        p2.duty_u16(duty)
        sleep(dtime)
    led.on()
    for i in range(0,65535,step):
        duty = 65535-i
        p2.duty_u16(duty)
        sleep(dtime)
