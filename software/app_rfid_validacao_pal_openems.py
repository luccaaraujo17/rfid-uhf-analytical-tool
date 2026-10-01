# -*- coding: utf-8 -*-
"""Aplicativo Streamlit de validação: modelo analítico x openEMS x bancada.

Execução:
    streamlit run app_rfid_validacao_pal_openems.py
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rfid_physics_core import (
    AntennaProfile,
    TagProfile,
    LinkBudgetInput,
    compute_link_budget,
    comparison_metrics,
    monte_carlo_link_budget,
    tag_axis_orientation_loss_db,
)

st.set_page_config(page_title="RFID PAL90209H - validação", layout="wide")
st.title("RFID UHF - esperado x openEMS x bancada")
st.caption(
    "Modelo analítico baseado em Friis/link budget, perfil real da antena Laird PAL90209H "
    "e tag aproximada de 75 x 20 mm. Valores experimentais são comparação, não constantes universais."
)

ANT = AntennaProfile()
TAG = TagProfile()


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def parse_filename(name: str) -> dict:
    n = normalize_text(name)
    def grab(pattern, default=None):
        m = re.search(pattern, n)
        return int(m.group(1)) if m else default
    if "deitada" in n:
        orientation = "90° horizontal/pitch"
    elif re.search(r"90\s*gr", n):
        orientation = "90° lateral/yaw"
    else:
        orientation = f"{grab(r'(\d+)\s*gr', 0)}° frontal"
    return {
        "arquivo": name,
        "distancia_cm": grab(r"(\d+)\s*cm"),
        "potencia_dbm": grab(r"(\d+)\s*db"),
        "n_tags": grab(r"(\d+)\s*tags?", 1),
        "n_antenas": grab(r"(\d+)\s*ant", 1),
        "orientacao": orientation,
        "material": "toalha" if ("toalha" in n or "tolha" in n) else "sem toalha",
    }


def read_jrfid(uploaded) -> pd.DataFrame:
    raw = uploaded.getvalue()
    if len(raw) < 100:
        return pd.DataFrame()
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig", errors="replace"))))
    if len(rows) < 3:
        return pd.DataFrame()
    header = [x.strip().replace(";;", "") for x in rows[1]]
    records = []
    for row in rows[2:]:
        if not row or not any(str(x).strip() for x in row):
            continue
        if len(row) == len(header) + 1:
            h = header[:-1] + ["DRM", header[-1]]
        else:
            h = header + [f"EXTRA_{i}" for i in range(max(0, len(row)-len(header)))]
        records.append(dict(zip(h, row)))
    df = pd.DataFrame(records)
    if df.empty or "RSSI" not in df.columns:
        return pd.DataFrame()
    meta = parse_filename(uploaded.name)
    for k,v in meta.items():
        df[k] = v
    df["RSSI"] = pd.to_numeric(df["RSSI"], errors="coerce")
    if "TAG ID" in df.columns:
        df["tag_curta"] = df["TAG ID"].astype(str).str[-6:]
    else:
        df["tag_curta"] = "TAG"
    return df.dropna(subset=["RSSI"])

with st.sidebar:
    st.header("Perfil de equipamento")
    st.write(f"**Antena:** {ANT.manufacturer} {ANT.model}")
    st.write(f"**Polarização:** {ANT.polarization}")
    st.write(f"**Ganho:** {ANT.peak_gain_dbic:.1f} dBic")
    st.write(f"**HPBW:** {ANT.hpbw_azimuth_deg:.0f}°")
    st.write(f"**Tag:** {TAG.description}")
    st.warning("O modelo/chip da tag é desconhecido; sensibilidade, ganho e carga são parâmetros iniciais.")

    st.header("Entrada nominal")
    distance_m = st.number_input("Distância antena-tag (m)", 0.10, 20.0, 1.00, 0.05)
    power_mode = st.selectbox(
        "Interpretação da potência",
        [
            "FIELDSTRENGTH ≈ potência conduzida (provisório)",
            "FIELDSTRENGTH + offset calibrado",
            "Potência conduzida medida",
        ],
    )
    fieldstrength_value = st.slider("FIELDSTRENGTH / potência informada (dB ou dBm)", 0.0, 33.0, 20.0, 1.0)
    power_offset_db = 0.0
    if power_mode == "FIELDSTRENGTH + offset calibrado":
        power_offset_db = st.number_input(
            "Offset FIELDSTRENGTH → potência conduzida (dB)", -20.0, 20.0, 0.0, 0.1
        )
    conducted_dbm = fieldstrength_value + power_offset_db
    st.caption(
        f"Potência conduzida usada no cálculo: {conducted_dbm:.2f} dBm. "
        "O mapeamento deve permanecer identificado até ser confirmado por documentação ou medição."
    )
    cable_loss_db = st.number_input("Perda de cabo e conectores (dB)", 0.0, 10.0, 1.0, 0.1)
    off_axis_deg = st.slider("Ângulo fora do eixo da antena (°)", 0.0, 180.0, 0.0, 1.0)
    pol_loss = st.number_input("Perda CP-LP nominal (dB)", 0.0, 10.0, 3.0, 0.1)
    orientation_mode = st.radio("Orientação da tag", ["Perda informada", "Eixo dipolar 3D"], horizontal=False)
    if orientation_mode == "Perda informada":
        orientation_loss = st.number_input("Perda extra por orientação (dB)", 0.0, 30.0, 0.0, 0.5)
        dipole_axis = [0.0, 1.0, 0.0]
    else:
        st.caption("Direção de propagação adotada: +X. Informe o eixo longitudinal da tag.")
        ax = st.number_input("Eixo tag X", -1.0, 1.0, 0.0, 0.1)
        ay = st.number_input("Eixo tag Y", -1.0, 1.0, 1.0, 0.1)
        az = st.number_input("Eixo tag Z", -1.0, 1.0, 0.0, 0.1)
        dipole_axis = [ax, ay, az]
        try:
            orientation_loss = tag_axis_orientation_loss_db([1,0,0], dipole_axis)
        except ValueError:
            orientation_loss = 0.0
            st.error("O eixo da tag não pode ser nulo.")
        st.metric("Perda 3D calculada", f"{orientation_loss:.2f} dB")
    material_loss = st.number_input("Perda de material em um sentido (dB)", 0.0, 50.0, 0.0, 0.5)
    backscatter_loss = st.number_input("Perda equivalente de backscatter (dB)", 0.0, 80.0, 28.0, 1.0)
    reader_sensitivity = st.number_input("Sensibilidade do leitor (dBm)", -120.0, -30.0, -90.0, 1.0)
    st.header("Tag aproximada")
    tag_gain_dbi = st.number_input("Ganho aproximado da tag (dBi)", -10.0, 5.0, 0.0, 0.5)
    tag_sensitivity_dbm = st.number_input("Limiar de ativação aproximado da tag (dBm)", -30.0, -5.0, -18.0, 0.5)

TAG_ACTIVE = TagProfile(**{
    **TAG.__dict__,
    "gain_dbi": float(tag_gain_dbi),
    "activation_threshold_dbm": float(tag_sensitivity_dbm),
})

def fieldstrength_to_conducted(value: float) -> float:
    return float(value) + float(power_offset_db)

inp = LinkBudgetInput(
    distance_m=distance_m,
    conducted_power_dbm=conducted_dbm,
    cable_loss_db=cable_loss_db,
    antenna_off_axis_deg=off_axis_deg,
    polarization_loss_db=pol_loss,
    orientation_extra_loss_db=orientation_loss,
    material_one_way_loss_db=material_loss,
    backscatter_equivalent_loss_db=backscatter_loss,
    reader_sensitivity_dbm=reader_sensitivity,
)
result = compute_link_budget(inp, ANT, TAG_ACTIVE)

c1,c2,c3,c4 = st.columns(4)
c1.metric("EIRP estimada", f"{result.eirp_dbm:.2f} dBm")
c2.metric("Potência na tag", f"{result.p_tag_dbm:.2f} dBm")
c3.metric("Retorno estimado", f"{result.p_rx_dbm:.2f} dBm")
c4.metric("Margem final", f"{result.final_margin_db:.2f} dB", result.classification)

st.subheader("Rastreabilidade do cálculo nominal")
st.dataframe(pd.DataFrame([result.as_dict()]).T.rename(columns={0:"valor"}), use_container_width=True)

with st.expander("Análise de incerteza Monte Carlo", expanded=True):
    n_mc = st.slider("Amostras", 500, 20000, 5000, 500)
    mc = monte_carlo_link_budget(inp, ANT, TAG_ACTIVE, n_samples=n_mc)
    m1,m2,m3 = st.columns(3)
    m1.metric("Prob. margem > 0", f"{100*mc['probability_margin_positive']:.1f}%")
    m2.metric("Prob. margem >= 6 dB", f"{100*mc['probability_margin_reliable']:.1f}%")
    m3.metric("P_rx p05-p95", f"{mc['p_rx_dbm']['p05']:.1f} a {mc['p_rx_dbm']['p95']:.1f} dBm")
    st.json(mc)

st.subheader("Matriz teórica para as distâncias e potências da bancada")
distances = [0.50, 1.00, 1.50, 2.00]
powers = [10, 15, 20, 25, 30]
rows=[]
for d in distances:
    for p in powers:
        r=compute_link_budget(LinkBudgetInput(
            distance_m=d,
            conducted_power_dbm=fieldstrength_to_conducted(p),
            cable_loss_db=cable_loss_db,
            antenna_off_axis_deg=0.0,
            polarization_loss_db=pol_loss,
            orientation_extra_loss_db=0.0,
            material_one_way_loss_db=0.0,
            backscatter_equivalent_loss_db=backscatter_loss,
            reader_sensitivity_dbm=reader_sensitivity,
        ), ANT, TAG_ACTIVE)
        rows.append({"distancia_cm":int(d*100),"potencia_dbm":p,"p_tag_dbm":r.p_tag_dbm,"p_rx_esperado_dbm":r.p_rx_dbm,"margem_final_db":r.final_margin_db,"classificacao":r.classification})
theory_df=pd.DataFrame(rows)
st.dataframe(theory_df, use_container_width=True)

fig=go.Figure()
for p,g in theory_df.groupby("potencia_dbm"):
    fig.add_trace(go.Scatter(x=g["distancia_cm"],y=g["p_rx_esperado_dbm"],mode="lines+markers",name=f"{p} dBm"))
fig.update_layout(title="Retorno analítico esperado por distância",xaxis_title="Distância (cm)",yaxis_title="P_rx estimado (dBm)")
st.plotly_chart(fig,use_container_width=True)

st.subheader("Importar CSVs do JRFID e comparar")
files=st.file_uploader("Selecione os CSVs",type=["csv"],accept_multiple_files=True)
if files:
    dfs=[read_jrfid(f) for f in files]
    dfs=[d for d in dfs if not d.empty]
    if not dfs:
        st.error("Nenhum arquivo válido com RSSI foi encontrado.")
    else:
        data=pd.concat(dfs,ignore_index=True)
        summary=(data.groupby(["arquivo","distancia_cm","potencia_dbm","n_tags","n_antenas","orientacao","material","tag_curta"],dropna=False)
                 .agg(n=("RSSI","count"),rssi_medio=("RSSI","mean"),rssi_std=("RSSI","std"),rssi_min=("RSSI","min"),rssi_max=("RSSI","max")).reset_index())
        # Comparação: uma etiqueta frontal, sem toalha
        cmp=summary[(summary.n_tags==1)&(summary.orientacao=="0° frontal")&(summary.material=="sem toalha")].copy()
        expected=[]
        for _,row in cmp.iterrows():
            r=compute_link_budget(LinkBudgetInput(
                distance_m=float(row.distancia_cm)/100.0,
                conducted_power_dbm=fieldstrength_to_conducted(float(row.potencia_dbm)),
                cable_loss_db=cable_loss_db,
                polarization_loss_db=pol_loss,
                backscatter_equivalent_loss_db=backscatter_loss,
                reader_sensitivity_dbm=reader_sensitivity,
            ),ANT,TAG_ACTIVE)
            expected.append(r.p_rx_dbm)
        cmp["p_rx_esperado_dbm"]=expected
        cmp["erro_bruto_db"]=cmp["rssi_medio"]-cmp["p_rx_esperado_dbm"]
        if len(cmp):
            offset=float(cmp["erro_bruto_db"].mean())
            cmp["p_rx_com_offset_dbm"]=cmp["p_rx_esperado_dbm"]+offset
            cmp["residuo_offset_db"]=cmp["rssi_medio"]-cmp["p_rx_com_offset_dbm"]
            raw_metrics=comparison_metrics(cmp["p_rx_esperado_dbm"],cmp["rssi_medio"])
            offset_metrics=comparison_metrics(cmp["p_rx_com_offset_dbm"],cmp["rssi_medio"])
            st.write("**Métricas sem calibração de offset**")
            st.json(raw_metrics)
            st.write(f"**Offset médio do leitor/conjunto:** {offset:.2f} dB")
            st.write("**Métricas após aplicar somente um offset global (sem alterar tendências físicas)**")
            st.json(offset_metrics)
        st.dataframe(summary,use_container_width=True)
        st.dataframe(cmp,use_container_width=True)
        st.download_button("Baixar comparação CSV",cmp.to_csv(index=False).encode("utf-8-sig"),"comparacao_esperado_experimental.csv","text/csv")


st.subheader("Importar resultados do openEMS")
st.caption(
    "Importe dois ou mais arquivos resultado.json. O aplicativo calcula correções relativas "
    "de potência na carga e RCS em relação a um cenário de referência. Essas correções não "
    "substituem Friis nem são convertidas diretamente em RSSI absoluto."
)
openems_files = st.file_uploader(
    "Resultados JSON do openEMS",
    type=["json"],
    accept_multiple_files=True,
    key="openems_results",
)
if openems_files:
    scenario_rows = []
    tag_rows = []
    for f in openems_files:
        try:
            obj = json.loads(f.getvalue().decode("utf-8"))
        except Exception as exc:
            st.error(f"Falha ao ler {f.name}: {exc}")
            continue
        sc = str(obj.get("scenario", f.name))
        rcs = obj.get("backscatter_rcs_m2")
        rcs_dbsm = 10.0 * math.log10(max(float(rcs), 1e-30)) if rcs is not None else np.nan
        scenario_rows.append({
            "arquivo": f.name,
            "cenario": sc,
            "frequencia_hz": obj.get("frequency_hz"),
            "chip_r_ohm": obj.get("chip_r_ohm"),
            "chip_c_pf": obj.get("chip_c_pf"),
            "rcs_m2": rcs,
            "rcs_dbsm": rcs_dbsm,
        })
        for tag_item in obj.get("tags", []):
            power = tag_item.get("load_power_w")
            power_dbw = 10.0 * math.log10(max(float(power), 1e-30)) if power is not None else np.nan
            tag_rows.append({
                "arquivo": f.name,
                "cenario": sc,
                "tag": tag_item.get("tag"),
                "load_power_w": power,
                "load_power_dbw": power_dbw,
                "probe_warning": tag_item.get("probe_warning", ""),
            })
    if scenario_rows:
        openems_scenarios = pd.DataFrame(scenario_rows)
        openems_tags = pd.DataFrame(tag_rows)
        baseline_name = st.selectbox(
            "Cenário de referência",
            openems_scenarios["cenario"].tolist(),
            index=0,
        )
        base_s = openems_scenarios.loc[openems_scenarios.cenario == baseline_name].iloc[0]
        openems_scenarios["delta_rcs_db"] = openems_scenarios["rcs_dbsm"] - float(base_s["rcs_dbsm"])
        if not openems_tags.empty:
            base_tag_rows = openems_tags[openems_tags.cenario == baseline_name].dropna(subset=["load_power_dbw"])
            base_tag_power = float(base_tag_rows["load_power_dbw"].mean()) if len(base_tag_rows) else np.nan
            openems_tags["delta_load_power_db"] = openems_tags["load_power_dbw"] - base_tag_power
        st.write("**Correção relativa de retroespalhamento por cenário**")
        st.dataframe(openems_scenarios, use_container_width=True)
        if not openems_tags.empty:
            st.write("**Correção relativa de potência na carga por tag**")
            st.dataframe(openems_tags, use_container_width=True)

        selected_sc = st.selectbox(
            "Cenário para aplicar como correção demonstrativa",
            openems_scenarios["cenario"].tolist(),
            index=0,
            key="selected_openems_correction",
        )
        sc_row = openems_scenarios.loc[openems_scenarios.cenario == selected_sc].iloc[0]
        delta_rcs = float(sc_row["delta_rcs_db"]) if pd.notna(sc_row["delta_rcs_db"]) else 0.0
        selected_tag_rows = openems_tags[openems_tags.cenario == selected_sc] if not openems_tags.empty else pd.DataFrame()
        delta_load = float(selected_tag_rows["delta_load_power_db"].mean()) if len(selected_tag_rows) else 0.0
        corrected_forward = result.p_tag_dbm + delta_load
        corrected_reverse = result.p_rx_dbm + delta_rcs
        corrected_final = min(
            corrected_forward - TAG_ACTIVE.activation_threshold_dbm,
            corrected_reverse - inp.reader_sensitivity_dbm,
        )
        k1, k2, k3 = st.columns(3)
        k1.metric("Δ potência na carga", f"{delta_load:.2f} dB")
        k2.metric("Δ RCS", f"{delta_rcs:.2f} dB")
        k3.metric("Margem corrigida demonstrativa", f"{corrected_final:.2f} dB")
        st.info(
            "A correção é relativa ao cenário selecionado como referência. Use-a para comparar "
            "orientações, materiais e proximidade; não a trate como calibração absoluta do RSSI."
        )
        export_compare = {
            "baseline": baseline_name,
            "selected_scenario": selected_sc,
            "delta_load_power_db": delta_load,
            "delta_rcs_db": delta_rcs,
            "analytical_nominal": result.as_dict(),
            "corrected_demonstration": {
                "p_tag_dbm": corrected_forward,
                "p_rx_dbm": corrected_reverse,
                "final_margin_db": corrected_final,
            },
        }
        st.download_button(
            "Baixar comparação app-openEMS JSON",
            json.dumps(export_compare, ensure_ascii=False, indent=2).encode("utf-8"),
            "comparacao_app_openems.json",
            "application/json",
        )

st.subheader("Exportar cenário para openEMS")
scenario={
    "schema":"rfid_openems_local_scene_v1",
    "method":"modelo local full-wave normalizado; distância/potência escaladas pelo app",
    "antenna":ANT.__dict__,
    "tag":TAG_ACTIVE.__dict__,
    "input":{
        **inp.__dict__,
        "power_interpretation": power_mode,
        "fieldstrength_value": fieldstrength_value,
        "fieldstrength_offset_db": power_offset_db,
        "tag_dipole_axis":dipole_axis,
    },
    "nominal_result":result.as_dict(),
    "openems_assumptions":{
        "excitation":"plane wave, linear, 1 V/m; aplicar 3 dB CP-LP no app",
        "eps_board_size_m":[0.030,0.335,0.295],
        "eps_epsilon_r_sweep":[1.02,1.05,1.10],
        "tag_chip_load_parametric":True,
        "warning":"openEMS fornece correções relativas; RSSI do JRFID inclui offset e processamento do leitor"
    }
}
st.download_button("Baixar JSON do cenário openEMS",json.dumps(scenario,ensure_ascii=False,indent=2).encode("utf-8"),"cenario_openems_exportado.json","application/json")
