# Pi Pico W: report internal temperature through MQTT

# based on:
# https://www.tomshardware.com/how-to/send-and-receive-data-raspberry-pi-pico-w-mqtt
# github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py
# J.Beale 26-Nov-2022

# needs local 'secrets.json' file in this format:
"""
{
  "wifi": {
    "ssid" : "MyWifiName",
    "pass": "MyWifiPassword"
  }

  "mqtt": {
    "server": "MyMQTTBroker",
    "user": "LocalDeviceName"
  }
}
"""

import network
import time
from machine import ADC, Pin, reset
from umqtt.simple import MQTTClient
import ujson

with open('secrets.json') as fp:
    secrets = ujson.loads(fp.read())
    
ssid = secrets['wifi']['ssid']     # my wifi router name
password = secrets['wifi']['pass'] # my wifi password

mqtt_server = secrets['mqtt']['server']
client_id =   secrets['mqtt']['user']
topic_pub =  'PicoTemp'

#print("Read SSID as: %s" % ssid)
#print("Read client ID as: %s" % client_id)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    wlan.connect(ssid, password)
while wlan.isconnected() == False:
    print('Waiting for connection...')
    time.sleep(2)
print(wlan.ifconfig())


def mqtt_connect():
    print("MQTT connect attempt: %s %s" % (client_id, mqtt_server))
    client = MQTTClient(client_id, mqtt_server, keepalive=3600)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
   print('Failed to connect to the MQTT Broker.')
   time.sleep(5)
   # reset()

try:
   client = mqtt_connect()
   print("Connected!")
except OSError as e:
   reconnect()

# --- Read sensor and report data
sensorTemp = ADC(4) 
degCfactor = 3.3 / (65535) 

while True:
    reading = sensorTemp.read_u16() * degCfactor
    degC = 27 - (reading - 0.706)/0.001721
    msg = "%.1f" % (degC)
    print (msg)
    client.publish(topic_pub, msg)

    time.sleep(5)
  
# Example output as seen from MQTT subscriber
# pi@rp49:~ $ mosquitto_sub -t '#' -F "%I, %t, %p"
# 2022-11-26T10:39:04-0800, PicoTemp, 19.6
# 2022-11-26T10:39:09-0800, PicoTemp, 19.6
# 2022-11-26T10:39:14-0800, PicoTemp, 18.6
# 2022-11-26T10:39:19-0800, PicoTemp, 18.6
# 2022-11-26T10:39:24-0800, PicoTemp, 17.7
    
