# -*- coding: utf-8 -*-
import argparse, json, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument("--mesh",default="rapida",choices=["rapida","media","fina"]); a=p.parse_args()
root=Path(__file__).resolve().parent
cfg=json.loads((root/"config_openems.json").read_text(encoding="utf-8"))
for s in cfg["scenarios"]:
    cmd=[sys.executable,str(root/"02_executar_cenario.py"),"--scenario",s["name"],"--mesh",a.mesh]
    print("EXECUTANDO"," ".join(cmd)); subprocess.run(cmd,check=True)
