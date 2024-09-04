import os
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
        requests.get("https://www.baidu.com",timeout=5)
        return True
    except Exception as e:
        print(e)
        return False
    
def connect():
    if not check():
        os.system(f"netsh wlan connect name={settings.WIFI_SSID}")
        return check()
    return True

def login():
    if not check_login():
        os.system(settings.SRUN_CMD)
        return check_login()
    return True
