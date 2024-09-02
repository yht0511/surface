# 执行任务
import json
import os
import sys
import time
import importlib
from rich import print

f=open("./procedure/procedure.json","r",encoding="utf-8")
procedures=json.loads(f.read())
f.close()

for procedure in procedures:
    print("执行任务: "+procedure["description"])
    try:
        module=importlib.import_module(procedure["path"])
    except Exception as e:
        print("[red]任务模块加载失败![/red]")
        print("[red]错误信息: "+str(e)+"[/red]")
        sys.exit(1)
    for step in procedure["steps"]:
        while True:
            try:
                print("    执行步骤: "+step["description"],end="  ")
                res=eval(f"module{step['path'].replace(procedure["path"],"")}")()
                if type(res)==str:
                    print(res)
                else:
                    print("[green]正常[/green]" if res else "[red]异常[/red]")
                break
            except Exception as e:
                print("[red]失败[/red]")
                print("    [red]错误信息: "+str(e)+"[/red]")
                print("    [red]3s后重试...[/red]",end="\r")
                time.sleep(3)





