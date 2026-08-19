# -*- coding: utf-8 -*-
import argparse, os, subprocess
from pathlib import Path
from openems_common import load_config, build_simulation

p=argparse.ArgumentParser()
p.add_argument("--scenario",default="S2_duas_tags_eps_frontal")
p.add_argument("--mesh",default="media",choices=["rapida","media","fina"])
a=p.parse_args()
root=Path(__file__).resolve().parent
cfg=load_config(root/"config_openems.json")
scenario=next(s for s in cfg["scenarios"] if s["name"]==a.scenario)
sim=build_simulation(cfg,scenario,a.mesh)
out=root/"resultados"/a.scenario
out.mkdir(parents=True,exist_ok=True)
xml=out/f"{a.scenario}.xml"
sim["CSX"].Write2XML(str(xml))
print("XML gerado:",xml)
try:
    subprocess.Popen([sim["AppCSXCAD_BIN"],str(xml)])
except Exception as exc:
    print("Abra manualmente no AppCSXCAD:",xml,"Erro:",exc)
