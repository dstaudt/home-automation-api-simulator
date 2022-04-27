import requests
from time import sleep
import os
from concurrent.futures import ThreadPoolExecutor

baseUrl = os.getenv('HOME_AUTO_BASEURL')

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
deviceIds = []

resp = requests.get(f'{baseUrl}/startTest', verify=False)
for profile in profiles:
    os.system(f'firefox -p {profile} -width 750 -height 600 -new-tab {baseUrl} &')
    sleep(2)

print('Browsers started: 0', '\r')
while True:
    sleep(3)
    resp = requests.get(f'{baseUrl}/deviceIds', verify=False)
    deviceIds = resp.text.splitlines()
    print(f'Browsers started: {len(deviceIds)}','\r')
    if  len(deviceIds) == len(profiles): break

def post_url(url, json):
    resp = requests.put(url=url, json=json, verify=False)
    print(f'PUT: {url}: Status: {resp.status_code}')
    return

pool = ThreadPoolExecutor(max_workers=12)

while True:
    for deviceId in deviceIds:
        try:
            pool.submit(post_url,url=f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": True} )
            pool.submit(post_url,url=f'{baseUrl}/lights/{deviceId}', json={ "lights_on": True} )
            pool.submit(post_url,url=f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": True} )
        except Exception as err:
            print(err)
    sleep(2)
    for deviceId in deviceIds:
        try:
            pool.submit(post_url,url=f'{baseUrl}/blinds/{deviceId}', json={ "blinds_down": False} )
            pool.submit(post_url,url=f'{baseUrl}/lights/{deviceId}', json={ "lights_on": False} )
            pool.submit(post_url,url=f'{baseUrl}/coffee/{deviceId}', json={ "coffee_on": False} )
        except Exception as err:
            print(err)
    sleep(2)


