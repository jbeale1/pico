# Python3 code to find and read data from Pi Pico board to Linux host
# 13-March-2021 J.Beale

import serial
import serial.tools.list_ports 

devPico = ""  # haven't found one yet

for port in serial.tools.list_ports.comports():
    if (port.vid == 11914) and (port.pid == 5): # IDs for Pico board
        devPico = port.name

if devPico != "":
    print("Found Pico connected at %s" % devPico)
else:
    print("No Pico board found.")
    exit()
        
ser = serial.Serial(port='/dev/'+devPico)

while True:
  print(ser.readline().rstrip().decode('utf-8'))
  
# Example Output:
#
# Found Pico connected at ttyACM1
# 225,449.765205,1.999999,0.100002,0.01222,0.01222,0.12222,0.12222,1.00000
# 226,451.765203,2.000008,0.100008,0.01222,0.01222,0.12221,0.12221,0.99999
# 227,453.765202,2.000002,0.100002,0.01222,0.01222,0.12222,0.12222,0.99998
# 228,455.765200,1.999995,0.099998,0.01222,0.01222,0.12222,0.12222,1.00000
# 229,457.765198,2.000007,0.100003,0.01222,0.01222,0.12222,0.12222,0.99999
