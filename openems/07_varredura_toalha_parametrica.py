# -*- coding: utf-8 -*-
"""Varredura paramétrica da toalha seca dobrada.

A espessura e as propriedades dielétricas não foram medidas. Este script evita
fixar um único material artificialmente preciso e executa combinações de
espessura, permissividade relativa e condutividade.
"""
import argparse
import copy
import json
from pathlib import Path

from openems_common import load_config, build_simulation, postprocess

p = argparse.ArgumentParser()
p.add_argument("--mesh", default="rapida", choices=["rapida", "media", "fina"])
p.add_argument("--limit", type=int, default=0, help="0 executa todas as combinações")
a = p.parse_args()

root = Path(__file__).resolve().parent
base_cfg = load_config(root / "config_openems.json")
t = base_cfg["towel"]
combinations = [
    (th, er, k)
    for th in t["thickness_sweep_mm"]
    for er in t["epsilon_r_sweep"]
    for k in t["kappa_s_m_sweep"]
]
if a.limit > 0:
    combinations = combinations[: a.limit]

for thickness, epsilon_r, kappa in combinations:
    cfg = copy.deepcopy(base_cfg)
    cfg["towel"]["size_mm"][0] = float(thickness)
    cfg["towel"]["epsilon_r"] = float(epsilon_r)
    cfg["towel"]["kappa_s_m"] = float(kappa)
    scenario = {
        "name": f"S7_toalha_t{thickness:g}mm_er{epsilon_r:g}_k{kappa:g}",
        "eps": False,
        "towel": True,
        "towel_overrides": {
            "size_mm": cfg["towel"]["size_mm"],
            "epsilon_r": epsilon_r,
            "kappa_s_m": kappa,
        },
        "tags": [{"offset_z_mm": 0.0, "orientation": "frontal"}],
    }
    sim = build_simulation(cfg, scenario, a.mesh)
    suffix = f"_{a.mesh}_R{sim['chip_r']:g}_C{sim['chip_c_pf']:g}pF"
    out = root / "resultados" / (scenario["name"] + suffix)
    out.mkdir(parents=True, exist_ok=True)
    sim["FDTD"].Run(str(out), cleanup=True, dump_statistics=True)
    result = postprocess(sim, out)
    result["towel_parameters"] = scenario["towel_overrides"]
    (out / "resultado.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Concluído:", out)
