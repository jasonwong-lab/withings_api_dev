#!/usr/bin/env python

from flask import Flask, request, redirect
import requests
import os
import configparser
import sys
import json
import time

_config = configparser.ConfigParser()
DEFAULT_CONFIG_FILES = []

LOCAL_CONFIG_PATH = "" # set path of config file i.e. "/home/user/withings_api_dev/project.conf"

print(LOCAL_CONFIG_PATH)

_config.read(DEFAULT_CONFIG_FILES + [LOCAL_CONFIG_PATH])

CLIENT_ID = _config.get('withings_api','client_id')
CUSTOMER_SECRET = _config.get('withings_api', 'customer_secret')
STATE = _config.get('withings_api', 'state')
ACCOUNT_URL = _config.get('withings_api', 'account_withings_url')
WBSAPI_URL = _config.get('withings_api', 'wbsapi_withings_url')
CALLBACK_URI = _config.get('withings_api', 'callback_uri')

app = Flask(__name__)

@app.route("/")
def get_code():
    """
    Route to get the permission from an user to take his data.
    This endpoint redirects to a Withings' login page on which
    the user has to identify and accept to share his data
    """
    payload = {'response_type': 'code',  # imposed string by the api
               'client_id': CLIENT_ID,
               'state': STATE,
               'scope': 'user.info',  # see docs for enhanced scope
               'redirect_uri': CALLBACK_URI  # URL of this app
#               'mode': 'demo'  # Use demo mode, DELETE THIS FOR REAL APP
               }

    r_auth = requests.get(f'{ACCOUNT_URL}/oauth2_user/authorize2',
                          params=payload)

    return redirect(r_auth.url)


@app.route("/demouser")
def demouser():
    return "<p>Hello, World!</p>"

@app.route("/get_token")
def get_token():
    """
    Callback route when the user has accepted to share his data.
    Once the auth has arrived Withings servers come back with
    an authentication code and the state code provided in the
    initial call
    """
    code = request.args.get('code')
    state = request.args.get('state')

    #payload in withings API post calls are in string format
    payload = 'action=requesttoken'+"&"+ \
	       'grant_type=authorization_code'+"&"+ \
               'client_id='+CLIENT_ID+"&"+ \
               'client_secret='+CUSTOMER_SECRET+"&"+  \
               'code='+code+"&"+ \
               'redirect_uri='+CALLBACK_URI


    #DEBUG: print(payload, file=sys.stderr)

    #requests are returned in JSON format
    r_token = requests.post(f'{WBSAPI_URL}/v2/oauth2',data=payload).json()

    #DEGBUG: print(r_token,file=sys.stderr)
    access_token = r_token['body']['access_token']

    # Below is for testing that the acquired access token can be used to retrieve information
    # about the users's device(s)
    headers = {'Authorization': 'Bearer ' + access_token}
    payload = 'action=getdevice'
    
    # List devices of returned user
    r_getdevice = requests.post(f'{WBSAPI_URL}/v2/user',
                               headers=headers,
                               params=payload).json()
                               
    #DEBUG: print(r_getdevice,file=sys.stderr)

    #return r_getdevice
	
    # List all samples of stethoscope
    #startdate=2024/2/29
    #enddate=1 minute ago
    offset = '00'                                          #x next available rows
    payload = 'action=list'+"&"+ \
               'startdate=1709136000'+"&"+ \
               'enddate='+str(int(time.time())-60)+"&"+ \
               'offset='+offset

    r_listdevice = requests.post('https://wbsapi.withings.net/v2/stetho',
                                headers=headers,
                                params=payload).json()

    #return r_listdevice

    # Get list of all signal id
    #sample_list = json.loads(r_listdevice)
    signalid_list = [series['signalid'] for series in r_listdevice['body']['series']]

    # Download all samples
    for signalid in signalid_list:
        payload = 'action=get'+"&"+ \
                  'signalid='+str(signalid)

        r_getsample = requests.post('https://wbsapi.withings.net/v2/stetho',
                                    headers=headers,
                                    params=payload).json()

        filename = f"{signalid}.json"
        with open(filename, 'w') as file:
            file.write(json.dumps(r_getsample))
