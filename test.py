import requests
from time import sleep
import os
from concurrent.futures import ThreadPoolExecutor

# baseUrl = "http://localhost:5000"
baseUrl = 'https://home-automation-api-simulator.herokuapp.com/'

profiles = [
    # 'Test01',
    # 'Test02',
    'Test03',
    'Test04',
    'Test05',
    'Test06',
    'Test07',
    'Test08'
]


# with open('device_ids.log', 'w'): pass

for profile in profiles:
    os.system(f'firefox -p {profile} -width 722 -height 582 -new-tab {baseUrl} &')
    sleep(3)

input('Waiting for browsers to spawn...')

with open('device_ids.log', 'r') as file:
    deviceIds = file.read().splitlines()

def post_url(url, json):
    return requests.put(url=url, json=json)

pool = ThreadPoolExecutor(max_workers=12)

while True:
    for deviceId in deviceIds:
        try:
            pool.submit(post_url,url=f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": True} )
            pool.submit(post_url,url=f'{baseUrl}/lights/{deviceId}', json={ "lights_on": True} )
            pool.submit(post_url,url=f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": True} )
        except Exception as err:
            print(err)
    sleep(5)
    for deviceId in deviceIds:
        try:
            pool.submit(post_url,url=f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": False} )
            pool.submit(post_url,url=f'{baseUrl}/lights/{deviceId}', json={ "lights_on": False} )
            pool.submit(post_url,url=f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": False} )
        except Exception as err:
            print(err)
    sleep(5)


