#!/usr/bin/env python3

import os
import time
import asyncio
import requests
from kasa import SmartPlug
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

plugIP = os.getenv('plugIP')
low = int(os.getenv('low', 40))
high = int(os.getenv('high', 55))
minRunTime = int(os.getenv('minRunTime', 900))
sleepTime = int(os.getenv('sleepTime', 180))
APIKEY = os.getenv('APIKEY')
DEVID = os.getenv('DEVID')
influxBucket = os.getenv('influxBucket')
influxOrg = os.getenv('influxOrg')
influxToken = os.getenv('influxToken')
influxURL = os.getenv('influxURL')
influxMeasurement = os.getenv('influxMeasurement')

version = '0.1'
UA_STRING = "/".join(
    ("sbhum.py", version)
)


def c2f(celsius):
    return (celsius * 9/5) + 32


def readSensor(sbURL, sbHeaders):
    r = requests.get(sbURL, headers=sbHeaders)
    # return array of (degF, rHum)
    return (round(c2f(r.json()['body']['temperature']), 1),
            r.json()['body']['humidity'])


def writeLogEntry(message, status):
    print(time.strftime("[%d %b %Y %H:%M:%S %Z]",
          time.localtime()) + " {}: {}".format(message, status))


async def plugOff(ip):
    p = SmartPlug(ip)
    await p.update()
    await p.turn_off()


async def plugOn(ip):
    p = SmartPlug(ip)
    await p.update()
    await p.turn_on()


async def readConsumption(ip):
    p = SmartPlug(ip)
    await p.update()
    watts = await p.current_consumption()
    return(watts)


def main():
    # True Min Run time should be the specified interval less the
    # regular sleep time
    realMinRunTime = minRunTime - sleepTime
    url = "/".join(
        ("https://api.switch-bot.com/v1.0/devices",
         DEVID,
         "status")
    )
    headers = {'Authorization': APIKEY}
    influxClient = InfluxDBClient(url=influxURL, token=influxToken,
                                  org=influxOrg)
    write_api = influxClient.write_api(write_options=SYNCHRONOUS)
    writeLogEntry('Startup', UA_STRING)
    while True:
        (degF, rH) = readSensor(url, headers)
        watts = asyncio.run(readConsumption(plugIP))
        record = [
            {
                "measurement": influxMeasurement,
                "fields": {
                    "degF": degF,
                    "rH": rH,
                    "power": watts
                }
            }
        ]
        write_api.write(bucket=influxBucket, record=record)
        if rH >= high:
            # kick on dehumidifier for min run time
            asyncio.run(plugOn(plugIP))
            writeLogEntry('Change state to ON, rH', rH)
            time.sleep(realMinRunTime)
        elif rH < low:
            asyncio.run(plugOff(plugIP))
            writeLogEntry('Change state to OFF, rH', rH)
        else:
            pass
        time.sleep(sleepTime)


if __name__ == "__main__":
    main()
