import time
import requests
import settings
from urllib.parse import unquote
import json

def list_devices():
    res=requests.post("https://songguoyun.topwd.top/Esp_Api_advance.php",json={
        "sgdz_account": settings.wake_username,
        "sgdz_password": settings.wake_password,
        "type": 1
    },timeout=2).text
    return json.loads(unquote(res))['deviceslist']

def set_power(name,state):
    """控制电源状态(True:开机,False:关机,reboot:强制重启,force_shutdown:强制关机)
    """
    map={
        True:1,
        False:0,
        0:0,
        -1:0,
        1:1,
        "shutdown":0,
        "boot":1,
        "start":1,
        "poweron":1,
        "reboot":2,
        "restart":2,
        "force_restart":2,
        "poweroff":14,
        "force_shutdown":14
    }
    res=requests.post("https://songguoyun.topwd.top/Esp_Api_new.php",json={
        "sgdz_account": settings.wake_username,
        "sgdz_password": settings.wake_password,
        "device_name":name,
        "value": map[state]
    },timeout=2).text
    if int(json.loads(unquote(res))["status"]) in [0,-1]:
        return True
    return False

def check():
    res=int(list_devices()[0]["status"])
    if res==2:
        raise Exception("设备离线,等待设备上线...")
    return res==1

def boot():
    if not check():
        set_power(list_devices()[0]["deviceName"],1)
        return check()
    return True