# -*- coding: utf-8 -*-
"""Gera correções relativas openEMS para importação no aplicativo.

A referência padrão é S0_tag_unica_ar_frontal. São calculadas diferenças em dB
de potência média na carga e RCS. Nenhum valor é convertido diretamente em RSSI.
"""
import argparse
import json
import math
from pathlib import Path
import pandas as pd

EPS = 1e-30
p = argparse.ArgumentParser()
p.add_argument("--reference", default="S0_tag_unica_ar_frontal")
a = p.parse_args()
root = Path(__file__).resolve().parent

records = []
for file in (root / "resultados").rglob("resultado.json"):
    d = json.loads(file.read_text(encoding="utf-8"))
    powers = [float(t.get("load_power_w", 0.0)) for t in d.get("tags", []) if t.get("load_power_w") is not None]
    positive = [x for x in powers if x > 0]
    mean_power = sum(positive) / len(positive) if positive else 0.0
    records.append({
        "scenario": d.get("scenario"),
        "path": str(file.parent),
        "chip_r_ohm": d.get("chip_r_ohm"),
        "chip_c_pf": d.get("chip_c_pf"),
        "backscatter_rcs_m2": d.get("backscatter_rcs_m2"),
        "mean_load_power_w": mean_power,
        "number_of_tags": len(d.get("tags", [])),
        "towel_parameters": d.get("towel_parameters"),
    })

if not records:
    raise SystemExit("Nenhum resultado.json encontrado.")

df = pd.DataFrame(records)
ref_rows = df[df["scenario"].astype(str).str.startswith(a.reference)]
if ref_rows.empty:
    raise SystemExit(f"Referência não encontrada: {a.reference}")
ref = ref_rows.iloc[0]
ref_p = max(float(ref["mean_load_power_w"]), EPS)
ref_rcs = max(float(ref["backscatter_rcs_m2"]), EPS)

df["delta_load_power_db"] = 10 * df["mean_load_power_w"].clip(lower=EPS).map(lambda x: math.log10(x / ref_p))
df["delta_rcs_db"] = 10 * df["backscatter_rcs_m2"].clip(lower=EPS).map(lambda x: math.log10(x / ref_rcs))
df["reference_scenario"] = ref["scenario"]

out_dir = root / "resultados"
out_csv = out_dir / "correcoes_openems_para_app.csv"
out_json = out_dir / "correcoes_openems_para_app.json"
df.to_csv(out_csv, index=False, encoding="utf-8-sig")
out_json.write_text(json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(out_csv)
print(out_json)
print(df[["scenario", "delta_load_power_db", "delta_rcs_db"]])
