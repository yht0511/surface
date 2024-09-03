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
    # os.system(f"mstsc /v:{ip}:{settings.rdp_port} /f")
    f=open(settings.rdp_temp_file,"w")
    f.write(settings.rdp_file.replace("$$address$$",f"{ip}:{settings.rdp_port}"))
    f.close()
    os.system("mstsc ./temp.rdp")
    return True
    
ips=[]