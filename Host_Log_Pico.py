# Python3 host code to find connected Pico boards
# tested only from Raspberry Pi 4 host
#  needs PyUSB to find Pico in bootloader mode
#  'sudo apt install python-usb python3-usb'

# print and log timestamped output from Pico via USB serial port
# 15-March-2021 J.Beale

import usb.core

VID      = 0x2e8a  # Vendor Id: Raspberry Pi Pico device
BootID   = 0x0003  # Pico bootloader mode
PythonID = 0x0005  # Pico in MicroPython Serial Device mode

device = usb.core.find(idVendor=VID, idProduct=BootID, find_all=1)
pCountBoot = sum(1 for _ in device)   

device = usb.core.find(idVendor=VID, idProduct=PythonID, find_all=1)
pCountSerial = sum(1 for _ in device)   

print("%d Pico bootloader devices" % pCountBoot)
print("%d Pico serial devices" % pCountSerial)

# ---------------------------------------------
import serial
import serial.tools.list_ports 
from datetime import datetime  # for Y-M-D H:M:S time format
import time                    # for seconds since epoch

oName = "Pico Log v0.1"
picoDev = [] # haven't found any serial port Pico devices yet

for port in serial.tools.list_ports.comports():
    if (port.vid == 0x2e8a) and (port.pid == 0x0005): # Pico Serial        
        picoDev.append(port.name)

if len(picoDev) == 0:
    print("No Pico board found.")
    exit()

ser = []
for pd in picoDev:        
  ser.append( serial.Serial(port='/dev/'+pd) )
  print("Using Pico connected at %s" % pd)        

print("-------\n")

#if len(ser) < 2:
#  print("fewer than two Pico boards found.")
#  exit()

  #inLine = ser[0].readline().rstrip().decode('utf-8')
  #print(inLine)
  
pName = picoDev[0]  # port name of Pico sending data
  
with open("pLog.csv",'a') as f:
  tNow = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")  
  
  # print and save CSV file header  
  print("epoch, A, B, C, D")  
  print("# %s  Port:%s  Start: %s" % (oName,pName,tNow))
  f.write("epoch, A, B, C, D\n")
  f.write("# %s  Port:%s  Start: %s\n" % (oName,pName,tNow))
  
  lCount = 0   # count of lines received on serial port
  
  while True:
    absSec = time.time()
    inLine = ser[0].readline().rstrip().decode('utf-8')
    lCount += 1
    f.write("%d, %s\n" % (absSec,inLine)) 
    if (lCount % 10 == 0):
      f.flush()
    print("%d, %s" % (absSec, inLine))    
  
"""  
# Example Output in logfile:

epoch, A, B, C, D
# Pico Log v0.1  Port:ttyACM1  Start: 2021-03-15_12:51:10
1615837870, 1339691060, 1358277119, 1395675892, 1415989454
1615837874, 40100884, 61876246, 97432076, 118673029
1615837875, 41362220, 63784071, 103039419, 125012936
1615837876, 37548995, 61612957, 96121555, 119369861
"""
