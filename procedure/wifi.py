import os
import time
import settings
import requests

def check():
    try:
        requests.get("http://10.0.0.55",timeout=2)
        return True
    except:
        return False

def check_login():
    try:
        requests.get("https://www.bing.com",timeout=5)
        return True
    except Exception as e:
        return False
    
def connect():
    if not check():
        os.system(f"netsh wlan connect name={settings.WIFI_SSID}")
        return check()
    return True

def login():
    if not check_login():
        os.popen(settings.SRUN_CMD).read()
        return check_login()
    return True
