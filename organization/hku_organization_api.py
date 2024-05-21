import configparser
import getpass
import hashlib
import hmac
import keyring
import matplotlib.pyplot as plt
import requests
import sys
import time
import wave
from functools import wraps


if keyring.get_password("withings_hku_project", "secret") is None:
    keyring.set_password("withings_hku_project", "secret", getpass.getpass("Secret: "))


def call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result.json()["status"] != 0:
            raise Exception("Bad reply")
        return result.json()["body"]
    return wrapper


class ApiHandling:

    class ExpiringKey:
        """ Api keys that can expire with time or after being used """

        was_used = False

        def __init__(self, name, set_function, timeout_s):
            self.name = name
            self.set_function = set_function
            self.timeout = timeout_s
            # read from keyring if any non expired key is found
            self.__value = keyring.get_password(self.name, "value")
            self.__timestamp = keyring.get_password(self.name, "timestamp")
            self.__timestamp = int(self.__timestamp) if self.__timestamp else None

            if self.__value:
                print(f"Found a {self.name} in the keyring !", end=' ')
            if self.__timestamp:
                if time.time() - self.__timestamp > self.timeout:
                    print("But it has expired already.")
                else:
                    print(f"Still valid for {self.time_left} sec.")

        @property
        def value(self):
            if self.__timestamp and time.time() - self.__timestamp > self.timeout:
                print(f"{self.name} expired, now calling a new one...")
                self.__value = None
            if self.was_used is True:
                print(f"{self.name} already used, now calling a new one...")
                self.__value = None
            if not self.__value:
                self.value = self.set_function()
            return self.__value

        @value.setter
        def value(self, new_value):
            """set the value and reset the timeout count"""
            self.__value = new_value
            self.__timestamp = int(time.time())
            keyring.set_password(self.name, "value", self.__value)
            keyring.set_password(self.name, "timestamp", str(self.__timestamp))

        @property
        def time_left(self):
            return int(self.timeout - (time.time() - self.__timestamp))

        @property
        def is_valid(self):
            return self.__value and self.time_left > 0

    BASE_URL = "https://wbsapi.withings.net"
    CALLBACK_URI = "https://google.com/"

    _nonce = None

    def __init__(self, mail, client_id, mac_list=None):
        self.mail = mail
        self.client_id = client_id
        if mac_list is None:
            mac_list = '["00:24:e4:8b:77:3c"]'
        self.mac_list = mac_list

        self._code = self.ExpiringKey("code", self.__set_code, 600)
        self.access_token = self.ExpiringKey("access_token", self.__set_access_token, 3600)
        self.refresh_token = self.ExpiringKey("refresh_token", self.__set_refresh_token, 31536e3)

    @staticmethod
    def request(method, url, params=None, debug=True, **kwargs):
        """added debug print for each call"""
        api_method = getattr(requests, method)
        if debug:
            print(f"{method.upper()} {url}\n{params}")
        result = api_method(url, params, **kwargs)
        if debug:
            print("reply:", result.json(), "\n")
        return result

    def __set_code(self):
        reply = self.activate(self.mac_list)
        return reply['user']['code']

    def __set_access_token(self):
        reply = self.get_access_token()
        self.refresh_token.value = reply['refresh_token']
        return reply['access_token']

    def __set_refresh_token(self):
        reply = self.get_access_token()
        self.refresh_token.value = reply['refresh_token']
        return reply['refresh_token']

    @staticmethod
    def __get_secret():
        saved_secret = keyring.get_password("withings_hku_project", "secret")
        if saved_secret is None:
            print("secret is not set yet")
            sys.exit()
        return saved_secret

    def get_signature(self, action, nonce=None):
        if nonce is None:
            nonce = self._nonce
        message = '{},{},{}'.format(action, self.client_id, nonce).encode()
        signature = hmac.new(
            self.__get_secret().encode(),
            msg=message,
            digestmod=hashlib.sha256
        ).hexdigest()
        return signature

    def _get_nonce(self):
        timestamp = int(time.time())
        signature = self.get_signature("getnonce", timestamp)
        payload = {
            'action': 'getnonce',
            'client_id': self.client_id,
            'timestamp': timestamp,
            'signature': signature,
        }
        reply = self.request("get", f'{self.BASE_URL}/v2/signature', params=payload).json()
        self._nonce = reply['body']['nonce']

    @call
    def activate(self, mac):
        """ v2-user/activate
        - Create an account with the mail (if not existing yet)
        - Link a list of device to the account
        - Get the device information (model, id, ...)
        - Get the user code for all other calls available for 10 minutes
        """
        self._get_nonce()

        action = "activate"
        signature = self.get_signature(action)
        payload = {
            'action': action,
            'client_id': self.client_id,
            'email': self.mail,
            'mac_addresses': mac,
            'mailingpref': 1,
            'birthdate': 848166152,
            'measures': '[{"value": 190, "unit": -2, "type": 4},'
                        '{"value": 90, "unit": 0, "type": 1}]',
            'gender': 0,
            'preflang': "en_US",
            'timezone': "America/New_York",
            'shortname': "JDE",
            'external_id': "my-external-id",
            'unit_pref': '{"weight":1,"height":6,"distance":6,"temperature":11}',
            'nonce': self._nonce,
            'signature': signature
        }
        return self.request("post", f'{self.BASE_URL}/v2/user', params=payload)

    @call
    def get_access_token(self, refresh: bool = True, with_secret: bool = False):
        action = "requesttoken"

        payload = {
            'action': action,
            'client_id': self.client_id
        }

        if with_secret is True:
            payload.update({
                'client_secret': self.__get_secret()
            })
        else:  # with signature
            self._get_nonce()
            signature = self.get_signature(action)
            payload.update({
                'nonce': self._nonce,
                'signature': signature,
            })

        if refresh is True and self.refresh_token.is_valid:
            payload.update({
                'grant_type': "refresh_token",
                'refresh_token': self.refresh_token.value
            })
        else:
            payload.update({
                'grant_type': 'authorization_code',
                'code': self._code.value,
                'redirect_uri': self.CALLBACK_URI
            })
            self._code.was_used = True

        return self.request("get", f'{self.BASE_URL}/v2/oauth2', params=payload)

    @call
    def stetho_list(self, start_date_utc=None, end_date_utc=None, offset=None):
        action = "list"
        payload = {
            'action': action
        }
        if start_date_utc is not None:
            payload['startdate'] = start_date_utc
        if start_date_utc is not None:
            payload['enddate'] = end_date_utc
        if offset is not None:
            payload['offset'] = offset

        header = {'Authorization': 'Bearer ' + self.access_token.value}

        return self.request("get", f'{self.BASE_URL}/v2/stetho', headers=header, params=payload)

    @call
    def stetho_get(self, signal_id):
        action = "get"
        payload = {
            'action': action,
            'signalid': signal_id,
        }

        header = {'Authorization': 'Bearer ' + self.access_token.value}

        return self.request("get", f'{self.BASE_URL}/v2/stetho', headers=header, params=payload)

    @call
    def hearth_v2_list(self, start_date_utc=None, end_date_utc=None, offset=None):
        action = "list"
        payload = {
            'action': action
        }
        if start_date_utc is not None:
            payload['startdate'] = start_date_utc
        if start_date_utc is not None:
            payload['enddate'] = end_date_utc
        if offset is not None:
            payload['offset'] = offset

        header = {'Authorization': 'Bearer ' + self.access_token.value}

        return self.request("get", f'{self.BASE_URL}/v2/heart', headers=header, params=payload)

    @call
    def hearth_v2_get(self, signal_id):
        action = "get"
        payload = {
            'action': action,
            'signalid': signal_id,
        }

        header = {'Authorization': 'Bearer ' + self.access_token.value}

        return self.request("get", f'{self.BASE_URL}/v2/heart', headers=header, params=payload)

    @staticmethod
    def alaw_decode(c):
        """A-law G 711 4 kHz sampling to 16 bit PCM signal decoding method"""
        c ^= 0x55
        m = c & 0x0F
        e = (c & 0x70) >> 4
        if e > 0:
            m |= 0x10
        m <<= 4
        m |= 0x08
        if e > 1:
            m <<= e - 1
        if c < 0x80:
            m = -m
        return m


def get_signal_from_list(api):
    signal_id_list = api.stetho_list()['series']
    if not signal_id_list:
        print("No signal found")
        sys.exit()

    for i, signal in enumerate(signal_id_list):
        print(i, '-', time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(signal['timestamp'])))
    signal_index = int(input("Enter signal number: "))
    return signal_id_list[signal_index]


def save_signal(name: str, pcm_signal_bytes: bytearray, frequency: int, sampling_bytes_width=2):
    with wave.open(name, 'wb') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(sampling_bytes_width)
        wav_file.setframerate(frequency)
        wav_file.writeframes(pcm_signal_bytes)


def stetho_signal_full_fetch(api, file_name=None, debug=False):

    # 1. choose signal amongst the available ones
    signal_info = get_signal_from_list(api)
    signal_id = signal_info['signalid']
    # signal_utc = signal_info['timestamp']
    # signal_device = signal_info['hash_deviceid']

    # 2. get the signal selected
    signal_data = api.stetho_get(signal_id)
    frequency = signal_data['frequency']
    signal = signal_data['signal']

    # 3. signal decoding if required (currently not trustworthy)
    # if signal_data['format'] == 1:  # signal is A-law encoded, decoding to pcm 16 bits
    #     pcm_signal = []
    #     for byte in signal:
    #         pcm_signal.append(api.alaw_decode(byte))
    #     signal = pcm_signal

    if debug:
        plt.plot(signal)
        plt.show()

    # 4. convert to bytearray and save to wav sound file
    if file_name:
        pcm_bytes = bytearray()
        for sample in signal:
            # Convert each sample to little-endian 16-bit PCM
            pcm_bytes += int(sample).to_bytes(2, byteorder='little', signed=True)
        save_signal(file_name, pcm_bytes, frequency)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")

    api = ApiHandling(
        mail=config.get('WITHINGS_API', 'user_mail'),
        client_id=config.get('WITHINGS_API', 'client_id')
    )

    stetho_signal_full_fetch(api, "output.wav")
