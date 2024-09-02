import requests
import settings 
import os

def getip():
    global ips
    ips=requests.get(settings.ip_url).json()
    if not ips:
        raise Exception("无法获取IP")
    return ips[0]

def connect():
    if not ips:
        ip=getip()
    else:
        ip=ips[0]
    os.system(f"mstsc /v:{ip}:{settings.rdp_port} /f")
    return True
    
ips=[]