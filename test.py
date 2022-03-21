import requests
from time import sleep
import os
# from os.path import exists
from pygtail import Pygtail

baseUrl = "http://localhost:5000"
# baseUrl = 'https://home-automation-api-simulator.herokuapp.com/'

profiles = [
    # 'Test01',
    # 'Test02',
    # 'Test03',
    # 'Test04',
    'Test05',
    'Test06',
    'Test07',
    'Test08'
]


with open('device_ids.log', 'w'): pass

for profile in profiles:
    os.system(f'firefox -p {profile} -width 722 -height 582 -new-tab {baseUrl} &')

input('Waiting for browsers to spawn...')

with open('device_ids.log', 'r') as file:
    deviceIds = file.read().splitlines()

while True:
    for deviceId in deviceIds:
        response = requests.request("PUT", f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": True})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
        response = requests.request("PUT", f'{baseUrl}/lights/{deviceId}', json={ "lights_on": True})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
        response = requests.request("PUT", f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": True})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
    sleep(2)
    for deviceId in deviceIds:
        response = requests.request("PUT", f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": False})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
        response = requests.request("PUT", f'{baseUrl}/lights/{deviceId}', json={ "lights_on": False})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
        response = requests.request("PUT", f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": False})
        if not response.status_code == 204: print(f'ID: {deviceId} response {response}')
    sleep(2)


