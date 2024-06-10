#!/usr/bin/env python3

import os
import asyncio
import logging
import requests
import secrets
from hashlib import sha256
import hmac
from base64 import b64encode
import time
from kasa import SmartPlug
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# --- To be passed in to container ---
# Required Vars
PLUG_IP = os.getenv('PLUG_IP')
LOW = int(os.getenv('LOW', 40))
HIGH = int(os.getenv('HIGH', 55))
MIN_RUN_TIME = int(os.getenv('MIN_RUN_TIME', 900))
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 180))
TOKEN = os.getenv('TOKEN')
SECRET = os.getenv('SECRET')
DEVID = os.getenv('DEVID')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_URL = os.getenv('INFLUX_URL')
INFLUX_MEASUREMENT = os.getenv('INFLUX_MEASUREMENT')

# Optional Vars
DEBUG = int(os.getenv('DEBUG', 0))

# --- Other Globals ---
VER = '1.0.3'
UA_STRING = f"sbhum.py/{VER}"
URL = 'https://api.switch-bot.com/v1.1/devices/{}/status'

# Setup logger
LOG_LEVEL = 'DEBUG' if DEBUG else 'INFO'
logging.basicConfig(level=LOG_LEVEL,
                    format='[%(levelname)s] %(asctime)s %(message)s',
                    datefmt='[%d %b %Y %H:%M:%S %Z]')
logger = logging.getLogger()


def c2f(celsius: float) -> float:
    return (celsius * 9/5) + 32


def build_headers(secret: str, token: str) -> dict:
    nonce = secrets.token_urlsafe()
    t = int(round(time.time() * 1000))
    string_to_sign = f'{token}{t}{nonce}'
    b_string_to_sign = bytes(string_to_sign, 'utf-8')
    b_secret = bytes(secret, 'utf-8')
    sign = b64encode(hmac.new(b_secret, msg=b_string_to_sign,
                              digestmod=sha256).digest())
    headers = {
        'Authorization': token,
        't': str(t),
        'sign': sign,
        'nonce': nonce
    }
    return headers


def build_url(url_template: str, devid: str) -> str:
    return url_template.format(devid)


def read_sensor(devid: str, secret: str, token: str) -> list:
    url = build_url(URL, devid)
    headers = build_headers(secret, token)
    r = requests.get(url, headers=headers)
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
    return watts


def main() -> None:
    # True Min Run time should be the specified interval less the
    # regular sleep time
    real_min_run_time = MIN_RUN_TIME - SLEEP_TIME
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN,
                                   org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    logger.info(f"Startup: {UA_STRING}")
    while True:
        (deg_f, rel_hum) = read_sensor(DEVID, SECRET, TOKEN)
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
            time.sleep(real_min_run_time)
        elif rel_hum <= LOW:
            asyncio.run(plug_off(PLUG_IP))
            logger.info(f"Change state to OFF, rH: {rel_hum}")
        else:
            pass
        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
