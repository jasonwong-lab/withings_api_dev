#!/usr/bin/env python

from flask import Flask, request, redirect
import requests
import os
import configparser
import sys
import json
import wave
from array import array

# Refresh the tokens
def get_token(DB_PATH):

    access_f = open(DB_PATH, 'r')

    line = access_f.readline()[:-1]
    REFRESH_TOKEN = line.split(":")[2]
    access_f.close()

    payload = 'action=requesttoken'+"&"+ \
                'grant_type=refresh_token'+"&"+ \
                'client_id='+CLIENT_ID+"&"+ \
                'client_secret='+CUSTOMER_SECRET+"&"+  \
                'refresh_token='+REFRESH_TOKEN

    r_token = requests.post(f'{WBSAPI_URL}/v2/oauth2',data=payload).json()

#    print(r_token)
    access_token = r_token['body']['access_token']
    refresh_token = r_token['body']['refresh_token']
    userid = r_token['body']['userid']

    write_f = open(DB_PATH, 'w')
    write_f.write(str(userid)+":"+str(access_token)+":"+str(refresh_token)+"\n")
    write_f.close()

    return access_token


def download_stetho(signalid):

    # Download specific signalid to wave format

    payload = 'action=get'+"&"+ \
              'signalid='+str(signalid)

    r_getsample = requests.post('https://wbsapi.withings.net/v2/stetho',
                                headers=headers,
                                params=payload).json()

    signal = r_getsample['body']['signal']
    vhd = r_getsample['body']['vhd']
    print ("Downloading to "+SOUND_PATH+str(signalid)+"_"+str(vhd)+".wav")

    # Convert signal directly into an array of bytes and then save to wave file.
    arr = b""
    for i in signal:
        arr += i.to_bytes(2, byteorder='little', signed=True)
    with wave.open(SOUND_PATH+str(signalid)+"_"+str(vhd)+".wav", 'wb') as wavfile:
        wavfile.setparams((1, 2, 2000, 0, 'NONE', 'NONE'))
        wavfile.writeframes(arr)


# Get config data
_config = configparser.ConfigParser()
DEFAULT_CONFIG_FILES = []

LOCAL_CONFIG_PATH = #### Enter path for local config file 

#print(LOCAL_CONFIG_PATH)

_config.read(DEFAULT_CONFIG_FILES + [LOCAL_CONFIG_PATH])

CLIENT_ID = _config.get('withings_api','client_id')
CUSTOMER_SECRET = _config.get('withings_api', 'customer_secret')
STATE = _config.get('withings_api', 'state')
ACCOUNT_URL = _config.get('withings_api', 'account_withings_url')
WBSAPI_URL = _config.get('withings_api', 'wbsapi_withings_url')
CALLBACK_URI = _config.get('withings_api', 'callback_uri')
DB_PATH = _config.get('withings_api', 'db_path')
SOUND_PATH = _config.get('withings_api', 'sound_path')

ACCESS_TOKEN = get_token(DB_PATH)

headers = {'Authorization': 'Bearer ' + ACCESS_TOKEN}
payload = 'action=list'+"&"+ \
           'startdate=1684500157'+"&"+ \
    	   'enddate=1716122557'+"&"+ \
    	   'offset=0'

r_signals = requests.post(f'{WBSAPI_URL}/v2/stetho',headers=headers,params=payload).json()


# Get list of all signal id
signalid_list = [series['signalid'] for series in r_signals['body']['series']]

for i in range(len(signalid_list)):
    download_stetho(signalid_list[i])

