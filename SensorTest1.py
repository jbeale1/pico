from machine import Pin  # for access to GPIO

led = Pin(25, Pin.OUT)               # set pin 25 (driving onboard LED) to output
inA = Pin(16, Pin.IN, Pin.PULL_UP)   # use this pin for input signal

while True:
    
    sensor = inA.value()
    
    if sensor == True:
        led.on()
    else:        
        led.off()
        
