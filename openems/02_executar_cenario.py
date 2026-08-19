# -*- coding: utf-8 -*-
import argparse, json
from pathlib import Path
from openems_common import load_config, build_simulation, postprocess

p=argparse.ArgumentParser()
p.add_argument("--scenario",default="S2_duas_tags_eps_frontal")
p.add_argument("--mesh",default="media",choices=["rapida","media","fina"])
p.add_argument("--chip-r",type=float,default=None)
p.add_argument("--chip-c-pf",type=float,default=None)
p.add_argument("--post-only",action="store_true")
a=p.parse_args()
root=Path(__file__).resolve().parent
cfg=load_config(root/"config_openems.json")
scenario=next(s for s in cfg["scenarios"] if s["name"]==a.scenario)
sim=build_simulation(cfg,scenario,a.mesh,a.chip_r,a.chip_c_pf)
suffix=f"_{a.mesh}_R{sim['chip_r']:g}_C{sim['chip_c_pf']:g}pF"
out=root/"resultados"/(a.scenario+suffix)
out.mkdir(parents=True,exist_ok=True)
if not a.post_only:
    sim["FDTD"].Run(str(out),cleanup=True,dump_statistics=True)
res=postprocess(sim,out)
(res_path:=out/"resultado.json").write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding="utf-8")
print("Resultado:",res_path)
print(json.dumps(res,ensure_ascii=False,indent=2))
