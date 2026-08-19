# -*- coding: utf-8 -*-
import json
from pathlib import Path
import pandas as pd
root=Path(__file__).resolve().parent
rows=[]
for f in (root/"resultados").rglob("resultado.json"):
    d=json.loads(f.read_text(encoding="utf-8"))
    base={k:d.get(k) for k in ["scenario","frequency_hz","chip_r_ohm","chip_c_pf","backscatter_rcs_m2"]}
    if d.get("tags"):
        for t in d["tags"]:
            rows.append({**base,**t,"path":str(f.parent)})
    else: rows.append({**base,"path":str(f.parent)})
df=pd.DataFrame(rows)
out=root/"resultados"/"resultados_consolidados.csv"
df.to_csv(out,index=False,encoding="utf-8-sig")
print(out)
print(df)
