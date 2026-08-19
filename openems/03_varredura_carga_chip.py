# -*- coding: utf-8 -*-
import argparse, json, subprocess, sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--scenario",default="S1_tag_unica_eps_frontal")
p.add_argument("--mesh",default="rapida",choices=["rapida","media","fina"])
a=p.parse_args()
root=Path(__file__).resolve().parent
cfg=json.loads((root/"config_openems.json").read_text(encoding="utf-8"))
Rs=[10,20,30,40]
Cs=[0.7,1.0,1.3,1.7]
for r in Rs:
    for c in Cs:
        cmd=[sys.executable,str(root/"02_executar_cenario.py"),"--scenario",a.scenario,"--mesh",a.mesh,"--chip-r",str(r),"--chip-c-pf",str(c)]
        print("EXECUTANDO"," ".join(cmd))
        subprocess.run(cmd,check=True)
