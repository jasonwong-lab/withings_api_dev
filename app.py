#!/usr/bin/env python

from flask import Flask, request, redirect
import requests
import os
import configparser
import sys
import json

_config = configparser.ConfigParser()
DEFAULT_CONFIG_FILES = []

LOCAL_CONFIG_PATH = ### enter location of your {LOCAL_CONFIG_PATH} file

print(LOCAL_CONFIG_PATH)

_config.read(DEFAULT_CONFIG_FILES + [LOCAL_CONFIG_PATH])

CLIENT_ID = _config.get('withings_api','client_id')
CUSTOMER_SECRET = _config.get('withings_api', 'customer_secret')
STATE = _config.get('withings_api', 'state')
ACCOUNT_URL = _config.get('withings_api', 'account_withings_url')
WBSAPI_URL = _config.get('withings_api', 'wbsapi_withings_url')
CALLBACK_URI = _config.get('withings_api', 'callback_uri')
DB_PATH = _config.get('withings_api', 'db_path')

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
               'scope': 'user.info,user.metrics,user.activity',  # see docs for enhanced scope
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

    payload = 'action=requesttoken'+"&"+ \
	       'grant_type=authorization_code'+"&"+ \
               'client_id='+CLIENT_ID+"&"+ \
               'client_secret='+CUSTOMER_SECRET+"&"+  \
               'code='+code+"&"+ \
               'redirect_uri='+CALLBACK_URI


    print(payload, file=sys.stderr)


    r_token = requests.post(f'{WBSAPI_URL}/v2/oauth2',data=payload).json()

    print(r_token,file=sys.stderr)
    access_token = r_token['body']['access_token']
    refresh_token = r_token['body']['refresh_token']
    userid = r_token['body']['userid']

    f = open("db_path", 'w')
    f.write(userid+":"+access_token+":"+refresh_token+"\n")
    f.close()

    # GET Some info with this token
    headers = {'Authorization': 'Bearer ' + access_token}
    payload = 'action=getdevice'

    #print(headers,file=sys.stderr)

    # List devices of returned user
    r_getdevice = requests.post(f'{WBSAPI_URL}/v2/user',
                               headers=headers,
                               params=payload).json()

    #print(r_getdevice,file=sys.stderr)

    # Download a list of stethoscope signals

    # GET list of stethoscope signals
    headers = {'Authorization': 'Bearer ' + access_token}
    payload = 'action=list'+"&"+ \
              'startdate=1684500157'+"&"+ \
	          'enddate=1716122557'+"&"+ \
	          'offset=0'

    r_signals = requests.post(f'{WBSAPI_URL}/v2/stetho',
                               headers=headers,
                               params=payload).json()

    signal_list = r_signals['body']['series']

    print(signal_list,file=sys.stderr)

    # GET actual signal

    cur_id = signal_list[0]['signalid']

    print(cur_id,file=sys.stderr)

    headers = {'Authorization': 'Bearer ' + access_token}
    payload = 'action=get'+"&"+ \
              'signalid='+str(cur_id)

    r_cursignal = requests.post(f'{WBSAPI_URL}/v2/stetho',
                               headers=headers,
                               params=payload).json()



    return r_cursignal
