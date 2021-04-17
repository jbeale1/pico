# MicroPython code for Raspberry Pi Pico
# Read data from MAX30102 sensor over I2C
# calculate pulse (bpm) and R, from which SpO2 could be derived
#  ...if you could calibrate it, which is non-trivial
# SpO2 calc: www.ncbi.nlm.nih.gov/pmc/articles/PMC4099100/
# 16-April-2021 J.Beale

from machine import Pin, I2C
from time import sleep_ms, ticks_ms, ticks_diff, localtime

# Write 'data' byte(s) to 'addr', on I2C device address AdrI2C
def wdat(addr,data):  
  i2c.writeto_mem(AdrI2C, addr, bytearray(list(data)) )
  sleep_ms(4)  # chip locks up with < 2 ms delay here
  
# Read n bytes from 'addr', on I2C device AdrI2C  
def rdat(addr,n):
  sleep_ms(1)
  return( list(i2c.readfrom_mem(AdrI2C, addr, n)) )

# ------------------------------------------
led1 = Pin(25, Pin.OUT)  # onboard LED
led1.off()
chA = Pin(13,Pin.IN,Pin.PULL_UP)  # input signal (switch) as flag

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000) 
res = i2c.scan() # get all devices on this I2C bus

AdrI2C = res[0]  # communicate with this I2C device address

# MAX30102 I2C address: 0xAE = decimal 174  =   1010_1110
# however, part actually reads 0x57 = dec 87 =  0101_0111 

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
f2 = 0.015    # final LP3 filter fraction

warmupCycles = 200  # how many values to run before printing
Red = 0  # initialize reading sum/avg
IR = 0
pCnt = 0   # how many averages computed
rLP = 0    # low-pass filtered version of Red signal
iLP = 0    # low-pass filtered version of IR signal
rLP2 = 0   # low-pass filtered version of Red signal
iLP2 = 0   # low-pass filtered version of IR signal
rHP2 = 0   # Red 2-pole highpass, and slight lowpass
iHP2 = 0   # IR highpass
rLP3 = 0   # Red low-pass filtered version of rHP2
iLP3 = 0   # IR lowpass
pkTrackR = -1000  # track red signal peak
ndTrackR = 1000   # track red signal nadir
pkTrackI = -1000  # track IR signal peak
ndTrackI = 1000   # track IR signal nadir
ctrTrackR = 0     # center of signal: (max-min)/2
rMax = 0  # absolute (non-decaying) max, min for previous cycle
rMin = 0
rMaxCap=0     # captured value of rMax
rMinCap=0     # captured value of rMin
iMaxCap=0     # captured value of rMax
iMinCap=0     # captured value of rMin
iMax = 0
iMin = 0
bpm=0         # beats per minute
rA = 0        # amplitude of red signal
iA = 0        # amplitude of red signal
R = 0         # ratio-of-ratios to calculate SpO2
Rf = 2        # LP filtered version of R
rUp = False   # true when rLP2 is >0 and larger than last sample
rDn = False   # true when rLP2 is <0 and less than last sample
iUp = False   # true when iLP2 is >0 and larger than last sample
iDn = False   # true when iLP2 is <0 and less than last sample
rUpOld = False  # if it was rising previous cycle
rDnOld = False  # if it was falling previous cycle
iUpOld = False  # if it was rising previous cycle
iDnOld = False  # if it was falling previous cycle

val = rdat(FIFODAT, 6)  # first read of sampled data

#sleep_ms(4000)  # delay to switch serial port
rOld = False
pInt = 500  # milliseconds per pulse
nInt = 0
pCnt = 0  # how many total readings
pulseCnt = 0 # how many detected pulses

now = localtime() # assumes host PC has updated it
startPulse = ticks_ms()
oldPulse = startPulse
dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])
    
# 400 Hz samples + 8 averages => 50 Hz output

while True:
  sleep_ms(2)
  valR = rdat(FIFORPT, 1)
  valW = rdat(FIFOWPT, 1)
  if (valR[0] != valW[0]):  # new data if read & write ptr not equal
    val = rdat(FIFODAT, 6)  # get 6 bytes (Red, IR reads, each 18 bits)
    Red = (val[0]&0x03)<<16 | val[1]<<8 | val[2]  # 18-bit Red sensor
    IR  = (val[3]&0x03)<<16 | val[4]<<8 | val[5]  # 18-bit IR sensor
    pCnt += 1               # track total # of readings
    
    rLP = int(rLP*(1-f) + f*Red)  # Red signal, lowpass (~ DC value)
    iLP = int(iLP*(1-f) + f*IR)   # IR signal, lowpass  (~ DC value)
    rHP = Red - rLP   # highpass = (x - lowpass)
    iHP = IR - iLP
    rLP2 = rLP2*(1-f) + f*rHP
    iLP2 = iLP2*(1-f) + f*iHP
    rHP2r = -(rHP - rLP2)   # highpass2 = (x - lowpass2)
    iHP2r = -(iHP - iLP2)
    rHP2 = 0.2*rHP2 + 0.8*rHP2r  # slight lowpass filter
    iHP2 = 0.2*iHP2 + 0.8*iHP2r  # slight lowpass filter
    rLP3 = rLP3*(1-f2) + f2*rHP2  # lowpass filtered version of rHP2
    iLP3 = iLP3*(1-f2) + f2*iHP2  # lowpass filtered version of rHP2
    
    if (pCnt <= warmupCycles):   # have not yet completed warmup cycles
        dF = 0.95  # peak-tracking exp. decay constant      
        ctrTrackR = (pkTrackR + ndTrackR)/2  # running midpoint (pk-valley)    
        pkTrackR *= dF       # exponential decay
        ndTrackR *= dF       # exponential decay
        pkTrackI *= dF       # exponential decay
        ndTrackI *= dF       # exponential decay   
        pkTrackR = max(pkTrackR,rHP2)  # update Red peak tracking
        ndTrackR = min(ndTrackR,rHP2)
        pkTrackI = max(pkTrackI,iHP2)  # update IR peak tracking
        ndTrackI = min(ndTrackI,iHP2)
    else:
        dF = 0.996  # slower tracking decay
        ctrTrack = (rMaxCap + rMinCap)/2
        ctrTrackR = ctrTrackR*0.95 + ctrTrack*0.05  # LP filtered version
        

    rDet = (rHP2 > ctrTrackR)  # is pulse above halfway point?

    if (rHP2 > rMax):  # new Red max?
        rUp = True     # set "red is rising" flag
        rMax = rHP2    # remember the new peak
    else:
        rUp = False
    if (rHP2>0) and rUpOld and (not rUp):    # first sample past max peak
        rMaxCap = rMax
        rA = (rMaxCap - rMinCap)  # Red signal peak-to-peak amplitude
        iA = (iMaxCap - iMinCap)  # IR signal pk-pk
        R = (rA/rLP) / (iA/iLP)   # SpO2 is a function of R
        Rf = 0.9*Rf + 0.1*R       # LP-filtered version of R
    rUpOld = rUp        
        
    if (rHP2 < rMin):  # new Red min?
        rDn = True     # set "red is falling" flag
        rMin = rHP2    # remember the new peak
    else:
        rDn = False
    if (rHP2<0) and rDnOld and (not rDn):  # first sample past min point
        rMinCap = rMin
    rDnOld = rDn
    
    if (iHP2 > iMax):  # new IR max?
        iUp = True     # set "IR is rising" flag
        iMax = iHP2    # remember the new peak
    else:
        iUp = False
    if (iHP2>0) and iUpOld and (not iUp):    # first sample past max peak
        iMaxCap = iMax  # capture the max point
          
    iUpOld = iUp        
        
    if (iHP2 < iMin):  # new IR min?
        iDn = True     # set "IR is falling" flag
        iMin = iHP2    # remember the new peak
    else:
        iDn = False
    if (iHP2<0) and iDnOld and (not iDn):  # first sample past min point
        iMinCap = iMin  # capture the minimum point
    iDnOld = iDn        

    rAmp = (pkTrackR - ndTrackR)  # Red channel AC amplitude
    iAmp = (pkTrackI - ndTrackI)  # IR channel AC amplitude
    
    #if (pCnt > warmupCycles):  # past warmup stage?
    #  print("%d,%d,%d,%d,%5.1f,%d" % (pCnt,rHP2,rMaxCap,rMinCap,bpm,Rf*1000))  # display Red and IR readings
    
    if (rDet != rOld):
            if (rDet): # rDet rising edge                
                pulseCnt += 1  # count of total pulses detected
                newPulse = ticks_ms()
                led1.on()      # LED signal                
                pInt = ticks_diff(newPulse,oldPulse)  # pulse interval, milliseconds
                bpm = 60000 / pInt  # beats per minute (pInt is in msec)
                oldPulse = newPulse
                if (bpm>300):  # almost surely an error
                    bpm=300
                inFlag = not chA.value()
                if (pCnt > warmupCycles) and (bpm>20):                
                  seconds = ticks_diff(newPulse,startPulse)/1E3  # time since beginning
                  print("%5.3f, %5.2f, %d, %d, %d, %d" % (seconds,bpm,nInt,rA,Rf*100,inFlag*40))
                rMax = 0
                iMax = 0
            else: # rDet falling edge
                negPulse = ticks_ms()
                nInt = ticks_diff(negPulse,newPulse)  # width of shorter part of pulse signal
                led1.off()      # LED signal
                rMin = 0
                iMin = 0
            rOld = rDet
            
    if (pCnt == warmupCycles):  # very last warmup reading? print CSV column headers
        print("time,bpm,nInt,rA,R,breath")
        print("# Start: %s" % dt_string)
# -----------------------------------------------------------
