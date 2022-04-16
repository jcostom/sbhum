#!/usr/bin/env python3

import os
import asyncio
import logging
import requests
from time import sleep
from kasa import SmartPlug
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

PLUG_IP = os.getenv('PLUG_IP')
LOW = int(os.getenv('LOW', 40))
HIGH = int(os.getenv('HIGH', 55))
MIN_RUN_TIME = int(os.getenv('MIN_RUN_TIME', 900))
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 180))
APIKEY = os.getenv('APIKEY')
DEVID = os.getenv('DEVID')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_URL = os.getenv('INFLUX_URL')
INFLUX_MEASUREMENT = os.getenv('INFLUX_MEASUREMENT')
DEBUG = int(os.getenv('DEBUG', 0))

VER = '0.5'
UA_STRING = f"sbhum.py/{VER}"

# Setup logger
logger = logging.getLogger()
ch = logging.StreamHandler()
if DEBUG:
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    ch.setLevel(logging.INFO)

formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(message)s',
                              datefmt='[%d %b %Y %H:%M:%S %Z]')
ch.setFormatter(formatter)
logger.addHandler(ch)


def c2f(celsius: float) -> float:
    return (celsius * 9/5) + 32


def read_sensor(sb_url: str, sb_headers: dict) -> list:
    r = requests.get(sb_url, headers=sb_headers)
    # return array of (degF, rHum)
    return [round(c2f(r.json()['body']['temperature']), 1),
            r.json()['body']['humidity']]


async def plug_off(ip: str) -> None:
    p = SmartPlug(ip)
    await p.update()
    await p.turn_off()


async def plug_on(ip: str) -> None:
    p = SmartPlug(ip)
    await p.update()
    await p.turn_on()


async def read_consumption(ip: str) -> float:
    p = SmartPlug(ip)
    await p.update()
    watts = await p.current_consumption()
    return(watts)


def main():
    # True Min Run time should be the specified interval less the
    # regular sleep time
    real_min_run_time = MIN_RUN_TIME - SLEEP_TIME
    url = f"https://api.switch-bot.com/v1.0/devices/{DEVID}/status"
    headers = {'Authorization': APIKEY}
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN,
                                   org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    logger.info(f"Startup: {UA_STRING}")
    while True:
        (deg_f, rel_hum) = read_sensor(url, headers)
        watts = asyncio.run(read_consumption(PLUG_IP))
        record = [
            {
                "measurement": INFLUX_MEASUREMENT,
                "fields": {
                    "degF": deg_f,
                    "rH": rel_hum,
                    "power": watts
                }
            }
        ]
        write_api.write(bucket=INFLUX_BUCKET, record=record)
        if rel_hum >= HIGH:
            asyncio.run(plug_on(PLUG_IP))
            logger.info(f"Change state to ON, rH: {rel_hum}")
            # sleep for specified min run time, less standard sleep time,
            # we will still perform that sleep later anyhow.
            sleep(real_min_run_time)
        elif rel_hum < LOW:
            asyncio.run(plug_off(PLUG_IP))
            logger.info(f"Change state to OFF, rH: {rel_hum}")
        else:
            pass
        sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
