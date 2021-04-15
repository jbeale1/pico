# MicroPython code for Raspberry Pi Pico
# Read data from MAX30102 sensor over I2C
# 15-April-2021 J.Beale

from machine import Pin, I2C
from time import sleep_ms, ticks_ms, ticks_diff

# Write 'data' byte(s) to 'addr', on I2C device address AdrI2C
def wdat(addr,data):  
  i2c.writeto_mem(AdrI2C, addr, bytearray(list(data)) )
  sleep_ms(4)  # chip locks up with < 2 ms delay here
  
# Read n bytes from 'addr', on I2C device AdrI2C  
def rdat(addr,n):
  sleep_ms(1)
  return( list(i2c.readfrom_mem(AdrI2C, addr, n)) )

#i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000) 
res = i2c.scan() # get all devices on this I2C bus

AdrI2C = res[0]  # communicate with this I2C device address

# MAX30102 I2C address: 0xAE = decimal 174  =   1010_1110
# however, part actually reads 0x57 = dec 87 =  0101_0111 
#print("I2C Device Address: ",AdrI2C)
#sleep_ms(20)

IntSta1 = 0x00  # Interrupt Status 1
IntSta2 = 0x01  # Interrupt Status 2
IntEnab = 0x02  # Interrupt Enable 1,2
FIFOWPT = 0x04  # FIFO write ptr
FIFO_OF = 0x05  # FIFO overflow counter
FIFORPT = 0x06  # FIFO read ptr
FIFODAT = 0x07  # FIFO data
FIFOCFG = 0x08  # FIFO configuration
ModeCfg = 0x09  # basic operating mode
SPO2Cfg = 0x0A  # SpO2 range & modes
LED1_PA = 0x0C  # LED 1 Pulse Amplitude
LED2_PA = 0x0D  # LED 2 Pulse Amplitude
LEDMode = 0x11  # 2 bytes; slots 1-4
DieTemp = 0x1F  # Die Temp 1,2
TempCfg = 0x21  # Die Temp Config
Part_ID = 0xFE  # Revision & Part ID #
# --------------------------------------------
smpAvgIdx = 3  # 0..5 => 1,2,4,8,16,32 samples averaged

res2 = rdat(Part_ID, 2)  # part ID and revision #
val  = rdat(IntSta1, 2)  # interrupt status (must read to enable)
wdat(ModeCfg,[0x03])     # SpO2 mode (Red & IR)
wdat(SPO2Cfg,[0x0f])     # 7: 100 sps, 411 usec pulse f:400
wdat(LED1_PA, [0x1f,0x1f]) # LED current amplitudes
wdat(LEDMode, [0x12,0x00])  # Slots 1-4 for Red,IR pulses
wdat(TempCfg,[1])        # start temp conversion
val = rdat(IntSta2,1)    # temperature interrupt
val = rdat(DieTemp,2)    # read sensor die temperature

cfgWord = smpAvgIdx << 5    # fifo config word
wdat(FIFOCFG,[cfgWord])  # fifo config averaging, rollover, int.

# Reset FIFO read & write pointers to 0
wdat(FIFOWPT,[0])
wdat(FIFORPT,[0])

f = 0.1      # low pass filter fraction
warmupCycles = 400  # how many values to run before printing
Red = 0  # initialize reading sum/avg
IR = 0
rCnt = 0  # how many readings we've added so far
pCnt = 0  # how many averages computed
rLP = 0   # low-pass filtered version of Red signal
iLP = 0   # low-pass filtered version of IR signal
rLP2 = 0   # low-pass filtered version of Red signal
iLP2 = 0   # low-pass filtered version of IR signal
pkTrackR = -1000  # track red signal peak
ndTrackR = 1000   # track red signal nadir

val = rdat(FIFODAT, 6)  # first read of sampled data

#sleep_ms(4000)  # delay to switch serial port
oldPulse = ticks_ms()
rOld = False
pInt = 500  # milliseconds per pulse

while True:
  valR = rdat(FIFORPT, 1)
  valW = rdat(FIFOWPT, 1)
  if (valR[0] != valW[0]):  # new data if read & write ptr not equal
    val = rdat(FIFODAT, 6)  # get 6 bytes (Red, IR reads, each 18 bits)
    Red = (val[0]&0x03)<<16 | val[1]<<8 | val[2]
    IR  = (val[3]&0x03)<<16 | val[4]<<8 | val[5]
    rCnt += 1
    if True:
      rLP = int(rLP*(1-f) + f*Red)
      iLP = int(iLP*(1-f) + f*IR)
      rHP = Red - rLP   # highpass = (x - lowpass)
      iHP = IR - iLP
      rLP2 = rLP2*(1-f) + f*rHP
      iLP2 = iLP2*(1-f) + f*iHP
      rHP2 = -(rHP - rLP2)   # highpass2 = (x - lowpass2)
      iHP2 = -(iHP - iLP2)
      pCnt += 1
      if (pCnt > warmupCycles):
        pkTrackR *= 0.995  # gradual decline of peak tracker
        ndTrackR *= 0.995
        ctrTrackR = (pkTrackR + ndTrackR)/2  # running midpoint (pk-valley)
        rDet = (rHP2 > ctrTrackR)
        pkTrackR = max(pkTrackR,rHP2)
        ndTrackR = min(ndTrackR,rHP2)
        rLPa = rLP - rLPoffset
        iLPa = iLP - iLPoffset
        if (rDet != rOld):
            if (rDet):
                newPulse = ticks_ms()
                pInt = ticks_diff(newPulse,oldPulse)
                oldPulse = newPulse
            rOld = rDet        
        print("%d,%d,%d,%d,%d" % (rHP2,iHP2,pkTrackR,ctrTrackR,pInt))  # display Red and IR readings
        
      else:        # have not yet completed warmup cycles
        rLPoffset = rLP
        iLPoffset = iLP
        if (pCnt == warmupCycles):  # very last warmup reading?
          print("Red, IR, rLP, iLP") # CSV column headers
      rCnt = 0

