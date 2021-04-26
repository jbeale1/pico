# Python3 host code to find connected Pico boards
# tested only from Raspberry Pi 4 host

# print and log timestamped output from Pico via USB serial port
# 2nd column in CSV file will be Unix Epoch time
# appends new data to log file each run, 
# does not over-write existing data from previous runs

# 26-April-2021 J.Beale

# ---------------------------------------------
import serial
import serial.tools.list_ports 
from datetime import datetime  # for Y-M-D H:M:S time format
import time                    # for seconds since epoch

logFileName = "/home/pi/Documents/pico/pLog.csv"

oName = "Pico Log v0.1"
picoDev = [] # haven't found any serial port Pico devices yet

while True:
  for port in serial.tools.list_ports.comports():
    if (port.vid == 0x2e8a) and (port.pid == 0x0005): # Pico Serial        
        picoDev.append(port.name)

  if len(picoDev) != 0:
    break
  time.sleep(1)  # wait and try again, until board is connected


print("Writing output to %s" % logFileName)
ser = []
for pd in picoDev:        
  ser.append( serial.Serial(port='/dev/'+pd) )
  
# use the first Pico board detected, if there was more than one  
pName = picoDev[0]  # port name of Pico sending data
  
with open(logFileName,'a') as f:
  lCount = 0   # count of lines received on serial port
  
  while True:
    tNow = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")  
    absSec = time.time()
    inLine = ser[0].readline().rstrip().decode('utf-8')
    lCount += 1
    f.write("%s, %d, %s\n" % (tNow,absSec,inLine)) 
    if (lCount % 10 == 0):
      f.flush()
    print("%d, %s" % (absSec, inLine))    
  
