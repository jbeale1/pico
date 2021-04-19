# MicroPython code for Raspberry Pi Pico
# communicate with MCP3424 18-bit ADC over I2C
# Find temperature from NTC thermistor
# write data out to USB and also SD card

from machine import Pin, I2C, SPI
from time import sleep_ms, localtime, time
import sdcard
import os
import sys
import math          # for natural log

# ----------------------------------------------
# Write 'data' byte(s) to I2C device at 'addr'
def wdat(addr,data):  
  i2c.writeto(addr, bytearray(list(data)) )
  sleep_ms(4)  # chip locks up with < 2 ms delay here
  
# Read n bytes from I2C device at 'addr'
def rdat(addr,n):
  sleep_ms(1)
  return( list(i2c.readfrom(addr, n)) )

def readT():
  buf = rdat(Adr,3)  # get 3-byte word (read more bytes for config data)
  val = (buf[0]&0x03)<<16 | buf[1]<<8 | buf[2]  # 18 bit result
  if (val & (1 << (bits - 1))) != 0:   # if sign bit is set        
        val = val - (1 << bits)        # ...find negative value

  Vadc = val * sf
  f = Vadc/Vb            # voltage fraction (Vadc / Vbridge)
  Rf = (0.5-f)/(0.5+f)   # resistor ratio R/Ro of thermistor
  T = (1 / (Tinv + (Binv * math.log(Rf)) ))-Tk  # calculate temperature
  return T

# ----------------------------------------------
sd_spi = SPI(1, sck = Pin(10, Pin.OUT), mosi = Pin(11, Pin.OUT),miso = Pin(12, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(13, Pin.OUT))

os.mount(sd, "/SD")
print("Mounted")
print("Size: {} MB".format(sd.sectors/2048))

flist = os.listdir("/SD")
#pathname = "/SD/" + flist[0]
for fn in flist:  # list files
  print(fn)

# sys.exit()  # stop here before writing anything

fname = "/SD/Tlog.csv" # file name to log data in
fp = open(fname,'a')   # open log and append new data
# --------------------------------------------

now = localtime() # assumes host PC has updated it
dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])
print("epoch, degC")  # CSV file header
print("# Start: %s" % dt_string) # start time/date

i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=100000) 
res = i2c.scan()
Adr = res[0]   # first device found on I2C bus. 0x68 for stock MCP3424

lnum = 0
bits = 18            # resolution of ADC mode in use
Nmax = 1 << (bits-1) # maximum value in this mode
Vref = 2.048         # ADC internal Vref
PGA = 1              # ADC gain setting (1,2,4,8)
Vb = 3.258           # bridge excitation voltage
sf = Vref/(Nmax * PGA)  # ADC scale factor in Volts/Count
Binv = 1.0/3380         # 1/B, where B is thermistor constant
Tk = 273.15             # offset from C to K
To = 25+Tk                 # Thermistor ref. temp, deg.C
Tinv = 1/To             # inverse of thermistor reference temp.

# Configure MCP3424 for continuous conversion in 18-bit mode
wdat(Adr,[0x1c])  # 0x1c: Ch1, AGC=1, 3.75 sps (18 bits)

fp.write("epoch, degC\n")  # CSV file header
fp.write("# Start: %s\n" % dt_string) # start time/date


avg = 4  # how many readings to average before printing
while True:
  Tsum = 0
  for i in range(avg):
    Tsum += readT()
    sleep_ms(280)
  T = Tsum/avg
  lnum += 1
  epoch = time()        # seconds from epoch (local time, not UTC)
  ostring = ("%d,%7.4f" % (epoch,T)) # temperature in degrees C
  print("%s" % ostring ) # temperature in degrees C
  fp.write("%s\n" % ostring)
  if (lnum % 3600) == 0:
      fp.flush()
      print("# hour: file flush")

fp.close()
os.umount("/SD")  # unmount card from filesystem

# ------------------------------------------------------- 
# https://www.mouser.com/datasheet/2/281/r44e-3685.pdf
# Murata NXRT15XH103FA1B020 10k 1% thermistor  B=3380 ±1% (25-50 C)
# R = R0 * exp(B * (1/T - 1/T0))
# T = 1 / ((1/B * ln(R/Ro)) + 1/To)
# R0 = 1E4, B = 3380, To = 25
# Full 4-element bridge: 3x 10k resistors, and 10k thermistor
# Bridge V+ = 3.258 V  ADC Vref = 2.048
