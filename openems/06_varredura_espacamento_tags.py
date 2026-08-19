# -*- coding: utf-8 -*-
"""Varre o espaçamento entre duas tags frontais no EPS.

Os resultados são relativos ao modelo aproximado de tag. O script não atribui
uma perda universal de acoplamento; ele quantifica como potência na carga e RCS
mudam com o espaçamento dentro das hipóteses do solver.
"""
import argparse
import json
from pathlib import Path

from openems_common import load_config, build_simulation, postprocess

p = argparse.ArgumentParser()
p.add_argument("--mesh", default="rapida", choices=["rapida", "media", "fina"])
p.add_argument("--spacings-mm", default="55,80,100,150,200")
p.add_argument("--chip-r", type=float, default=None)
p.add_argument("--chip-c-pf", type=float, default=None)
a = p.parse_args()

root = Path(__file__).resolve().parent
cfg = load_config(root / "config_openems.json")
spacings = [float(x) for x in a.spacings_mm.split(",") if x.strip()]

for spacing in spacings:
    center = 127.5  # mantém o par aproximadamente centralizado na placa de 295 mm
    h1 = center - spacing / 2
    h2 = center + spacing / 2
    scenario = {
        "name": f"S6_duas_tags_eps_espacamento_{spacing:g}mm",
        "eps": True,
        "tags": [
            {"height_mm": h1, "orientation": "frontal"},
            {"height_mm": h2, "orientation": "frontal"},
        ],
    }
    sim = build_simulation(cfg, scenario, a.mesh, a.chip_r, a.chip_c_pf)
    suffix = f"_{a.mesh}_R{sim['chip_r']:g}_C{sim['chip_c_pf']:g}pF"
    out = root / "resultados" / (scenario["name"] + suffix)
    out.mkdir(parents=True, exist_ok=True)
    sim["FDTD"].Run(str(out), cleanup=True, dump_statistics=True)
    result = postprocess(sim, out)
    result["spacing_mm"] = spacing
    (out / "resultado.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Concluído:", out)
