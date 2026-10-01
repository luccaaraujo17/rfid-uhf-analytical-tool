# -*- coding: utf-8 -*-
"""Aplicação Streamlit para análise do enlace RFID UHF, usando modelo analítico e dados experimentais."""

from __future__ import annotations

import json
import math
import os
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# CONSTANTES FÍSICAS

C0 = 299_792_458.0
EPS = 1e-12

# PRESETS FÍSICOS DE REFERÊNCIA

# Referência de potência: 4 W EIRP (36 dBm).
RF_PRESETS = {
    "Referência 4 W EIRP — moderado": {
        "eirp_limit_dbm": 36.0,
        "reader_sensitivity_dbm": -90.0,
        "tag_activation_dbm": -18.0,
        "reader_antenna_gain_dbi": 9.0,
        "tag_gain_dbi": 0.0,
        "cable_loss_db": 1.0,
        "backscatter_link_loss_db": 28.0,
        "polarization_loss_db": 3.0,
        "tag_orientation_extra_loss_db": 2.0,
        "textile_dry_db_per_m": 12.0,
        "textile_wet_db_per_m": 25.0,
        "reliable_margin_db": 6.0,
    },
    "Conservador": {
        "eirp_limit_dbm": 36.0,
        "reader_sensitivity_dbm": -85.0,
        "tag_activation_dbm": -18.0,
        "reader_antenna_gain_dbi": 9.0,
        "tag_gain_dbi": -1.0,
        "cable_loss_db": 1.0,
        "backscatter_link_loss_db": 32.0,
        "polarization_loss_db": 3.0,
        "tag_orientation_extra_loss_db": 4.0,
        "textile_dry_db_per_m": 18.0,
        "textile_wet_db_per_m": 35.0,
        "reliable_margin_db": 6.0,
    },
    "Pior caso severo": {
        "eirp_limit_dbm": 36.0,
        "reader_sensitivity_dbm": -85.0,
        "tag_activation_dbm": -18.0,
        "reader_antenna_gain_dbi": 9.0,
        "tag_gain_dbi": -3.0,
        "cable_loss_db": 1.5,
        "backscatter_link_loss_db": 38.0,
        "polarization_loss_db": 3.0,
        "tag_orientation_extra_loss_db": 8.0,
        "textile_dry_db_per_m": 25.0,
        "textile_wet_db_per_m": 45.0,
        "reliable_margin_db": 6.0,
    },
}

def watts_to_dbm(watts: float) -> float:
    return 10.0 * math.log10(max(watts, EPS) * 1000.0)

def dbm_to_watts(dbm: float) -> float:
    return 10.0 ** ((float(dbm) - 30.0) / 10.0)

def conducted_power_from_eirp(eirp_dbm: float, antenna_gain_dbi: float, cable_loss_db: float) -> float:
    return float(eirp_dbm) - float(antenna_gain_dbi) + float(cable_loss_db)

# Cena padrão

def default_scene() -> Dict[str, Any]:
    return {
        "schema": "rfid_hospitalar_physics_scene_v1",
        "units": "m",
        "description": "Cena padrão gerada internamente pelo app.",
        "rf": {
            "antenna_manufacturer": "Laird Technologies",
            "antenna_model": "PAL90209H",
            "antenna_polarization": "LHCP",
            "antenna_frequency_range_hz": [902e6, 928e6],
            "antenna_axial_ratio_db": 1.0,
            "antenna_max_vswr": 1.3,
            "antenna_size_m": [0.2591, 0.2591, 0.0335],
            "tag_model_status": "aproximado/paramétrico; etiqueta 75 x 20 mm sem identificação de chip",
            "frequency_hz": 915e6,
            "eirp_limit_dbm": 36.0,
            "reader_tx_power_dbm": 28.0,
            "reader_sensitivity_dbm": -90.0,
            "tag_activation_dbm": -18.0,
            "reader_antenna_gain_dbi": 9.0,
            "tag_gain_dbi": 0.0,
            "cable_loss_db": 1.0,
            "backscatter_link_loss_db": 28.0,
            "polarization_loss_db": 3.0,
            "tag_orientation_extra_loss_db": 2.0,
            "antenna_hpbw_deg": 70.0,
            "antenna_front_to_back_db": 20.0,
            "antenna_largest_dimension_m": 0.2591,
            "reliable_margin_db": 6.0,
        },
        "materials": {
            "MDF Cru": {
                "wall_crossing_loss_db": 4.0,
                "reflection_risk_db": 1.0,
                "description": "Dielétrico leve; não deve ser tratado como blindagem forte."
            },
            "Espuma Anecoica": {
                "wall_crossing_loss_db": 25.0,
                "reflection_risk_db": 0.5,
                "description": "Absorvedor RF aproximado; valor deve ser calibrado em bancada."
            },
            "Aço Inox": {
                "wall_crossing_loss_db": 80.0,
                "reflection_risk_db": 8.0,
                "description": "Metal condutor; bloqueio alto se for parede contínua; gera multipercurso."
            },
            "Acrílico/Policarbonato": {
                "wall_crossing_loss_db": 2.0,
                "reflection_risk_db": 0.5,
                "description": "Baixa perda; não confina campo sozinho."
            }
        },
        "cabin": {
            "center": [0.0, 0.0, 1.05],
            "size": [1.22, 1.18, 2.10],
            "wall_thickness_m": 0.06,
            "front_open": True,
            "front_y": -0.59,
            "default_wall_material": "Espuma Anecoica",
            "panels": [
                {"name": "left_wall",  "plane": "x", "coord": -0.61, "span_y": [-0.59, 0.59], "span_z": [0.0, 2.10], "material": "Espuma Anecoica"},
                {"name": "right_wall", "plane": "x", "coord":  0.61, "span_y": [-0.59, 0.59], "span_z": [0.0, 2.10], "material": "Espuma Anecoica"},
                {"name": "back_wall",  "plane": "y", "coord":  0.59, "span_x": [-0.61, 0.61], "span_z": [0.0, 2.10], "material": "Espuma Anecoica"},
                {"name": "ceiling",    "plane": "z", "coord":  2.10, "span_x": [-0.61, 0.61], "span_y": [-0.59, 0.59], "material": "Espuma Anecoica"}
            ]
        },
        "read_zone": {
            "center": [0.0, 0.0, 1.0],
            "size": [1.00, 1.00, 1.80],
            "z_min": 0.15,
            "z_max": 1.95
        },
        "cage": {
            "center": [0.0, 0.0, 0.91],
            "size": [0.67, 0.80, 1.60],
            "grid_pitch_m": [0.15, 0.27],
            "bar_diameter_m": 0.012,
            "extra_diffraction_loss_db": 1.5,
            "enabled": True
        },
        "textile_volume": {
            "center": [0.0, 0.0, 0.80],
            "size": [0.55, 0.62, 1.20],
            "attenuation_db_per_m_dry": 12.0,
            "attenuation_db_per_m_wet": 25.0,
            "enabled": True
        },
        "scale": {
            "center": [0.0, 0.0, 0.06],
            "size": [1.0, 1.0, 0.12],
            "metal_reflection_penalty_db": 2.0,
            "enabled": True
        },
        "antennas": [
            {"name": "ESQ",  "position": [-0.535, -0.03, 1.08], "normal": [ 1.0, 0.0, 0.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"},
            {"name": "DIR",  "position": [ 0.535, -0.03, 1.08], "normal": [-1.0, 0.0, 0.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"},
            {"name": "TOPO", "position": [ 0.0,   -0.03, 2.035],"normal": [ 0.0, 0.0,-1.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"}
        ],
        "tags": [
            {"name": "TAG_01", "position": [-0.22, -0.18, 0.45], "inside_expected": True},
            {"name": "TAG_02", "position": [ 0.21, -0.16, 0.65], "inside_expected": True},
            {"name": "TAG_03", "position": [-0.10,  0.11, 0.90], "inside_expected": True},
            {"name": "TAG_04", "position": [ 0.14,  0.18, 1.15], "inside_expected": True},
            {"name": "PROBE_LATERAL", "position": [1.45, 0.0, 1.0], "inside_expected": False},
            {"name": "PROBE_FRENTE", "position": [0.0, -1.85, 1.0], "inside_expected": False},
            {"name": "PROBE_PRATELEIRA", "position": [1.20, 0.55, 1.1], "inside_expected": False}
        ]
    }

# Cálculos auxiliares

def arr(v: Any) -> np.ndarray:
    return np.array(v, dtype=float)

def norm_vec(v: Any) -> np.ndarray:
    a = arr(v)
    n = np.linalg.norm(a)
    if n < EPS:
        return a
    return a / n

def lateral_normal(side: str, tilt_vertical_deg: float, yaw_deg: float) -> List[float]:
    """Normal das antenas laterais.

    Convenção:
    - tilt_vertical_deg < 0 aponta a antena para baixo.
    - yaw_deg > 0 aponta levemente para o fundo da cabine (+Y).
    - side='ESQ' aponta predominantemente para +X; side='DIR' para -X.
    """
    t = math.radians(float(tilt_vertical_deg))
    y = math.radians(float(yaw_deg))
    sign_x = 1.0 if side.upper().startswith('ESQ') else -1.0
    v = np.array([
        sign_x * math.cos(t) * math.cos(y),
        math.cos(t) * math.sin(y),
        math.sin(t),
    ], dtype=float)
    return norm_vec(v).tolist()

def top_normal(tilt_x_deg: float, tilt_y_deg: float) -> List[float]:
    """Normal da antena superior.

    Base: apontada para baixo [0, 0, -1].
    tilt_x_deg inclina em direção ao eixo X.
    tilt_y_deg inclina em direção ao eixo Y.
    """
    tx = math.radians(float(tilt_x_deg))
    ty = math.radians(float(tilt_y_deg))
    v = np.array([math.sin(tx), math.sin(ty), -math.cos(tx) * math.cos(ty)], dtype=float)
    return norm_vec(v).tolist()

def generate_stack_tags(
    n_random: int,
    n_buried_center: int,
    center: List[float],
    size: List[float],
    seed: int,
    distribution: str,
    center_concentration: float,
) -> List[Dict[str, Any]]:
    """Gera tags internas dentro do volume de enxoval.

    As tags geradas são pontos de teste físico, não obstáculos. O objetivo é
    avaliar zonas mortas no volume empilhado, especialmente no núcleo central.
    """
    rng = np.random.default_rng(int(seed))
    c = arr(center)
    s = arr(size)
    tags: List[Dict[str, Any]] = []

    n_random = max(0, int(n_random))
    n_buried_center = max(0, int(n_buried_center))
    center_concentration = float(np.clip(center_concentration, 0.0, 1.0))

    for i in range(n_random):
        if distribution == 'Camadas verticais':
            # Distribui em camadas Z para evitar buracos estatísticos no empilhamento.
            z_frac = ((i % max(n_random, 1)) + 0.5) / max(n_random, 1)
            z = c[2] - s[2] / 2.0 + z_frac * s[2]
            x = rng.uniform(c[0] - s[0] / 2.0, c[0] + s[0] / 2.0)
            y = rng.uniform(c[1] - s[1] / 2.0, c[1] + s[1] / 2.0)
        elif distribution == 'Centro mais denso':
            # Mistura uniforme + normal concentrada no centro.
            if rng.random() < center_concentration:
                x = rng.normal(c[0], max(s[0] / 7.0, 1e-3))
                y = rng.normal(c[1], max(s[1] / 7.0, 1e-3))
                z = rng.normal(c[2], max(s[2] / 5.0, 1e-3))
                x = float(np.clip(x, c[0] - s[0] / 2.0, c[0] + s[0] / 2.0))
                y = float(np.clip(y, c[1] - s[1] / 2.0, c[1] + s[1] / 2.0))
                z = float(np.clip(z, c[2] - s[2] / 2.0, c[2] + s[2] / 2.0))
            else:
                x = rng.uniform(c[0] - s[0] / 2.0, c[0] + s[0] / 2.0)
                y = rng.uniform(c[1] - s[1] / 2.0, c[1] + s[1] / 2.0)
                z = rng.uniform(c[2] - s[2] / 2.0, c[2] + s[2] / 2.0)
        else:
            x = rng.uniform(c[0] - s[0] / 2.0, c[0] + s[0] / 2.0)
            y = rng.uniform(c[1] - s[1] / 2.0, c[1] + s[1] / 2.0)
            z = rng.uniform(c[2] - s[2] / 2.0, c[2] + s[2] / 2.0)

        tags.append({
            'name': f'PILHA_{i+1:03d}',
            'position': [float(x), float(y), float(z)],
            'inside_expected': True,
        })

    # Tags centrais soterradas: coluna quase no eixo da pilha, útil para ver o miolo.
    for j in range(n_buried_center):
        z_frac = (j + 0.5) / max(n_buried_center, 1)
        z = c[2] - s[2] / 2.0 + z_frac * s[2]
        x = rng.normal(c[0], max(s[0] / 25.0, 0.005))
        y = rng.normal(c[1], max(s[1] / 25.0, 0.005))
        x = float(np.clip(x, c[0] - s[0] * 0.08, c[0] + s[0] * 0.08))
        y = float(np.clip(y, c[1] - s[1] * 0.08, c[1] + s[1] * 0.08))
        tags.append({
            'name': f'SOTERRADA_CENTRO_{j+1:02d}',
            'position': [float(x), float(y), float(z)],
            'inside_expected': True,
        })

    return tags

def update_named_antenna(scene: Dict[str, Any], name: str, position: List[float], normal: List[float]) -> None:
    for ant in scene.get('antennas', []):
        if ant.get('name') == name:
            ant['position'] = [float(v) for v in position]
            ant['normal'] = [float(v) for v in normal]
            return
    scene.setdefault('antennas', []).append({
        'name': name,
        'position': [float(v) for v in position],
        'normal': [float(v) for v in normal],
        'gain_dbi': float(scene.get('rf', {}).get('reader_antenna_gain_dbi', 9.0)),
        'hpbw_deg': float(scene.get('rf', {}).get('antenna_hpbw_deg', 70.0)),
        'polarization': 'LHCP',
    })

def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 10.0)

def linear_to_db(x: float) -> float:
    return 10.0 * math.log10(max(x, EPS))

def wavelength(freq_hz: float) -> float:
    return C0 / freq_hz

def fraunhofer_distance(freq_hz: float, largest_dimension_m: float) -> float:
    """Distância de campo distante aproximada: 2D²/λ."""
    lam = wavelength(freq_hz)
    return 2.0 * largest_dimension_m * largest_dimension_m / lam

def fspl_db(distance_m: float, freq_hz: float, min_distance_m: float) -> Tuple[float, bool]:
    """Perda em espaço livre.

    Friis só é rigorosamente válida no campo distante. Para evitar potência
    absurdamente alta no campo próximo, usamos d_eff=max(d, d_far) e sinalizamos
    quando a distância real está abaixo do limite.
    """
    d_real = max(float(distance_m), 1e-4)
    near_field = d_real < min_distance_m
    d_eff = max(d_real, min_distance_m)
    return 20.0 * math.log10(d_eff) + 20.0 * math.log10(freq_hz) - 147.55, near_field

def antenna_pattern_gain_db(
    peak_gain_dbi: float,
    angle_deg: float,
    hpbw_deg: float,
    front_to_back_db: float,
) -> float:
    """Aproximação parabólica de padrão de antena.

    A(θ) = -min(12*(θ/HPBW)^2, A_m)
    Com θ=HPBW/2, a perda é ~3 dB, coerente com definição de HPBW.
    """
    angle_deg = abs(float(angle_deg))
    hpbw_deg = max(float(hpbw_deg), 1.0)
    attenuation = min(12.0 * (angle_deg / hpbw_deg) ** 2, float(front_to_back_db))
    return float(peak_gain_dbi) - attenuation

def segment_aabb_length(p0: np.ndarray, p1: np.ndarray, center: np.ndarray, size: np.ndarray) -> float:
    """Comprimento do segmento p0-p1 que passa dentro de uma caixa AABB."""
    bmin = center - size / 2.0
    bmax = center + size / 2.0
    d = p1 - p0
    tmin, tmax = 0.0, 1.0
    for i in range(3):
        if abs(d[i]) < EPS:
            if p0[i] < bmin[i] or p0[i] > bmax[i]:
                return 0.0
        else:
            t1 = (bmin[i] - p0[i]) / d[i]
            t2 = (bmax[i] - p0[i]) / d[i]
            ta, tb = min(t1, t2), max(t1, t2)
            tmin = max(tmin, ta)
            tmax = min(tmax, tb)
            if tmax < tmin:
                return 0.0
    return max(0.0, tmax - tmin) * np.linalg.norm(d)

def point_in_aabb(p: np.ndarray, center: np.ndarray, size: np.ndarray) -> bool:
    bmin = center - size / 2.0
    bmax = center + size / 2.0
    return bool(np.all(p >= bmin - 1e-9) and np.all(p <= bmax + 1e-9))

def segment_intersects_aabb(p0: np.ndarray, p1: np.ndarray, center: np.ndarray, size: np.ndarray) -> Tuple[bool, float, float]:
    """Retorna se o segmento cruza a caixa e os parâmetros t de entrada/saída."""
    bmin = center - size / 2.0
    bmax = center + size / 2.0
    d = p1 - p0
    tmin, tmax = 0.0, 1.0
    for i in range(3):
        if abs(d[i]) < EPS:
            if p0[i] < bmin[i] or p0[i] > bmax[i]:
                return False, 0.0, 0.0
        else:
            t1 = (bmin[i] - p0[i]) / d[i]
            t2 = (bmax[i] - p0[i]) / d[i]
            ta, tb = min(t1, t2), max(t1, t2)
            tmin = max(tmin, ta)
            tmax = min(tmax, tb)
            if tmax < tmin:
                return False, 0.0, 0.0
    return True, tmin, tmax

def count_aabb_surface_crossings(p0: np.ndarray, p1: np.ndarray, center: np.ndarray, size: np.ndarray) -> int:
    """Conta cruzamentos de superfície de caixa para aproximar travessia de gaiola.

    0: caminho totalmente dentro ou totalmente fora sem atravessar
    1: entra ou sai da caixa
    2: atravessa de fora para fora
    """
    inside0 = point_in_aabb(p0, center, size)
    inside1 = point_in_aabb(p1, center, size)
    hit, t0, t1 = segment_intersects_aabb(p0, p1, center, size)
    if not hit:
        return 0
    if inside0 and inside1:
        return 0
    if inside0 != inside1:
        return 1
    # fora-fora; só conta se atravessou o interior entre 0 e 1
    if 0.0 <= t0 <= 1.0 or 0.0 <= t1 <= 1.0:
        return 2
    return 0

def grid_equivalent_loss_db(pitch_a_m: float, pitch_b_m: float, bar_diameter_m: float, extra_loss_db: float) -> float:
    """Perda equivalente simplificada de uma grade metálica aberta.

    A perda básica vem da fração aberta da célula. O termo extra_loss_db representa
    difração, espessura, soldas, orientação das barras e efeito do metal próximo.
    Deve ser calibrado em bancada.
    """
    open_a = max(pitch_a_m - bar_diameter_m, 1e-4)
    open_b = max(pitch_b_m - bar_diameter_m, 1e-4)
    cell_area = max(pitch_a_m * pitch_b_m, 1e-6)
    open_fraction = max(min((open_a * open_b) / cell_area, 1.0), 1e-4)
    return -10.0 * math.log10(open_fraction) + extra_loss_db

def plane_crossing_loss(
    p0: np.ndarray,
    p1: np.ndarray,
    panels: List[Dict[str, Any]],
    materials: Dict[str, Dict[str, float]],
    override_loss_db: Optional[float] = None,
) -> Tuple[float, List[str]]:
    """Soma perdas ao cruzar painéis definidos por planos retangulares."""
    d = p1 - p0
    loss = 0.0
    crossed = []
    for panel in panels:
        plane = panel.get("plane")
        coord = float(panel.get("coord"))
        axis = {"x": 0, "y": 1, "z": 2}[plane]
        if abs(d[axis]) < EPS:
            continue
        t = (coord - p0[axis]) / d[axis]
        if not (0.0 < t < 1.0):
            continue
        q = p0 + t * d
        ok = True
        if plane == "x":
            sy = panel.get("span_y", [-math.inf, math.inf])
            sz = panel.get("span_z", [-math.inf, math.inf])
            ok = sy[0] <= q[1] <= sy[1] and sz[0] <= q[2] <= sz[1]
        elif plane == "y":
            sx = panel.get("span_x", [-math.inf, math.inf])
            sz = panel.get("span_z", [-math.inf, math.inf])
            ok = sx[0] <= q[0] <= sx[1] and sz[0] <= q[2] <= sz[1]
        elif plane == "z":
            sx = panel.get("span_x", [-math.inf, math.inf])
            sy = panel.get("span_y", [-math.inf, math.inf])
            ok = sx[0] <= q[0] <= sx[1] and sy[0] <= q[1] <= sy[1]
        if ok:
            mat_name = panel.get("material", "MDF Cru")
            panel_loss = override_loss_db if override_loss_db is not None else float(materials.get(mat_name, {}).get("wall_crossing_loss_db", 0.0))
            loss += panel_loss
            crossed.append(panel.get("name", mat_name))
    return loss, crossed

# CARREGAMENTO DA CENA

def load_scene_from_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def find_default_json() -> Optional[Path]:
    candidates = [
        Path("rfid_scene_metadata.json"),
        Path("/mnt/data/rfid_scene_metadata.json"),
        Path.cwd() / "rfid_scene_metadata.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

# CÁLCULO DE LINK BUDGET

def compute_path_effects(
    ant: Dict[str, Any],
    point: np.ndarray,
    scene: Dict[str, Any],
    controls: Dict[str, float],
) -> Dict[str, Any]:
    rf = scene["rf"]
    materials = scene["materials"]
    p_ant = arr(ant["position"])
    n_ant = norm_vec(ant["normal"])
    v = point - p_ant
    d = float(np.linalg.norm(v))
    if d < 1e-5:
        d = 1e-5
    u = v / d

    cosang = float(np.clip(np.dot(n_ant, u), -1.0, 1.0))
    angle_deg = math.degrees(math.acos(cosang))
    g_reader = antenna_pattern_gain_db(
        peak_gain_dbi=float(ant.get("gain_dbi", controls["reader_antenna_gain_dbi"])),
        angle_deg=angle_deg,
        hpbw_deg=float(ant.get("hpbw_deg", controls["antenna_hpbw_deg"])),
        front_to_back_db=controls["antenna_front_to_back_db"],
    )

    d_far = fraunhofer_distance(controls["frequency_hz"], controls["antenna_largest_dimension_m"])
    fspl, near_field = fspl_db(d, controls["frequency_hz"], d_far)

    # Perda por parede da cabine/painéis. A abertura frontal não é painel.
    cabin_loss, crossed_panels = plane_crossing_loss(
        p_ant,
        point,
        scene.get("cabin", {}).get("panels", []),
        materials,
        override_loss_db=controls.get("override_wall_loss_db"),
    )

    # Perda equivalente da gaiola metálica.
    cage_loss = 0.0
    cage_crossings = 0
    cage = scene.get("cage", {})
    if cage.get("enabled", True) and controls["use_cage_loss"] > 0.5:
        cage_center = arr(cage.get("center", [0, 0, 0.9]))
        cage_size = arr(cage.get("size", [0.67, 0.80, 1.60]))
        cage_crossings = count_aabb_surface_crossings(p_ant, point, cage_center, cage_size)
        pitch = cage.get("grid_pitch_m", [0.15, 0.27])
        grid_loss = grid_equivalent_loss_db(
            float(pitch[0]),
            float(pitch[1]),
            float(cage.get("bar_diameter_m", 0.012)),
            controls["cage_extra_diffraction_loss_db"],
        )
        cage_loss = cage_crossings * grid_loss

    # Perda por tecido/enxoval como volume atenuador.
    textile_loss = 0.0
    textile_len = 0.0
    textile = scene.get("textile_volume", {})
    if textile.get("enabled", True) and controls["use_textile_loss"] > 0.5:
        textile_center = arr(textile.get("center", [0, 0, 0.8]))
        textile_size = arr(textile.get("size", [0.55, 0.62, 1.20]))
        textile_len = segment_aabb_length(p_ant, point, textile_center, textile_size)
        textile_loss = textile_len * controls["textile_attenuation_db_per_m"]

    # Penalidade determinística perto da balança metálica: não bloqueia, mas reduz margem
    # para representar risco de multipercurso destrutivo / campo não uniforme.
    multipath_penalty = 0.0
    scale = scene.get("scale", {})
    if scale.get("enabled", True) and controls["use_scale_multipath"] > 0.5:
        scale_center = arr(scale.get("center", [0, 0, 0.06]))
        scale_size = arr(scale.get("size", [1.0, 1.0, 0.12]))
        # Penaliza mais em até 30 cm acima da balança e dentro da projeção XY.
        inside_xy = (
            abs(point[0] - scale_center[0]) <= scale_size[0] / 2.0
            and abs(point[1] - scale_center[1]) <= scale_size[1] / 2.0
        )
        height_above = point[2] - (scale_center[2] + scale_size[2] / 2.0)
        if inside_xy and 0.0 <= height_above <= 0.30:
            factor = 1.0 - height_above / 0.30
            multipath_penalty = controls["scale_multipath_penalty_db"] * factor

    # Correção/diagnóstico opcional de multipercurso em cabine metálica (Inox).
    # Por padrão, fica apenas como verificação; só entra no link budget se o usuário habilitar
    # "Aplicar correção aproximada".
    inox_mp = inox_first_order_multipath_delta_db(
        ant=ant,
        point=point,
        scene=scene,
        controls=controls,
        direct_gain_eff_dbi=g_reader,
        direct_distance_m=d,
    )
    inox_multipath_loss = float(inox_mp.get("inox_multipath_loss_db", 0.0))

    total_medium_loss = cabin_loss + cage_loss + textile_loss + multipath_penalty + inox_multipath_loss

    return {
        "distance_m": d,
        "angle_deg": angle_deg,
        "reader_gain_dbi_eff": g_reader,
        "fspl_db": fspl,
        "near_field": near_field,
        "cabin_loss_db": cabin_loss,
        "crossed_panels": crossed_panels,
        "cage_loss_db": cage_loss,
        "cage_crossings": cage_crossings,
        "textile_loss_db": textile_loss,
        "textile_len_m": textile_len,
        "multipath_penalty_db": multipath_penalty,
        "inox_multipath_delta_db": float(inox_mp.get("inox_multipath_delta_db", 0.0)),
        "inox_multipath_loss_db": inox_multipath_loss,
        "inox_reflection_paths": int(inox_mp.get("inox_reflection_paths", 0)),
        "inox_multipath_note": inox_mp.get("inox_multipath_note", ""),
        "total_medium_loss_db": total_medium_loss,
    }

def db_to_lin(db: float) -> float:
    return 10.0 ** (float(db) / 10.0)

def lin_to_db(x: float) -> float:
    return 10.0 * math.log10(max(float(x), EPS))

def is_reflective_panel(panel: Dict[str, Any], scene: Dict[str, Any], controls: Dict[str, float]) -> bool:
    """Decide se um painel deve entrar na verificação de reflexão de Inox/metal.

    Observação: isso não prova blindagem real nem calcula VSWR; apenas identifica
    superfícies metálicas/altamente refletivas para o modelo aproximado de primeira ordem.
    """
    mat = str(panel.get("material", "")).lower()
    if any(k in mat for k in ["inox", "aço", "aco", "metal", "steel", "alumin"]):
        return True
    mats = scene.get("materials", {})
    loss = float(mats.get(panel.get("material", ""), {}).get("wall_crossing_loss_db", 0.0))
    if controls.get("override_wall_loss_db", 0.0) >= 40.0 and loss >= 40.0:
        return True
    return loss >= 40.0

def point_inside_panel_span(point: np.ndarray, panel: Dict[str, Any], tol: float = 1e-6) -> bool:
    plane = panel.get("plane")
    if plane == "x":
        sy = panel.get("span_y", [-1e9, 1e9]); sz = panel.get("span_z", [-1e9, 1e9])
        return sy[0]-tol <= point[1] <= sy[1]+tol and sz[0]-tol <= point[2] <= sz[1]+tol
    if plane == "y":
        sx = panel.get("span_x", [-1e9, 1e9]); sz = panel.get("span_z", [-1e9, 1e9])
        return sx[0]-tol <= point[0] <= sx[1]+tol and sz[0]-tol <= point[2] <= sz[1]+tol
    if plane == "z":
        sx = panel.get("span_x", [-1e9, 1e9]); sy = panel.get("span_y", [-1e9, 1e9])
        return sx[0]-tol <= point[0] <= sx[1]+tol and sy[0]-tol <= point[1] <= sy[1]+tol
    return False

def reflect_point_across_panel(point: np.ndarray, panel: Dict[str, Any]) -> np.ndarray:
    q = np.array(point, dtype=float).copy()
    plane = panel.get("plane")
    coord = float(panel.get("coord", 0.0))
    idx = {"x": 0, "y": 1, "z": 2}.get(plane, 0)
    q[idx] = 2.0 * coord - q[idx]
    return q

def line_intersection_with_panel_plane(p0: np.ndarray, p1: np.ndarray, panel: Dict[str, Any]) -> Optional[np.ndarray]:
    plane = panel.get("plane")
    coord = float(panel.get("coord", 0.0))
    idx = {"x": 0, "y": 1, "z": 2}.get(plane, None)
    if idx is None:
        return None
    denom = float(p1[idx] - p0[idx])
    if abs(denom) < 1e-12:
        return None
    t = (coord - p0[idx]) / denom
    if t < -1e-9 or t > 1.0 + 1e-9:
        return None
    return p0 + t * (p1 - p0)

def inox_first_order_multipath_delta_db(
    ant: Dict[str, Any],
    point: np.ndarray,
    scene: Dict[str, Any],
    controls: Dict[str, float],
    direct_gain_eff_dbi: float,
    direct_distance_m: float,
) -> Dict[str, Any]:
    """Estimativa de interferência por reflexões de primeira ordem em painéis metálicos.

    Modelo usado: método das imagens + soma complexa de campos no ponto.
    Não é full-wave, não calcula modos de cavidade nem S11/VSWR. Serve como
    alerta de risco de picos/vales por multipercurso em cabine de Inox.
    """
    if controls.get("use_inox_multipath", 0.0) <= 0.5:
        return {"inox_multipath_delta_db": 0.0, "inox_multipath_loss_db": 0.0, "inox_reflection_paths": 0, "inox_multipath_note": "desativado"}

    freq = float(controls["frequency_hz"])
    lam = wavelength(freq)
    k = 2.0 * math.pi / max(lam, EPS)
    gamma_mag = float(controls.get("inox_reflection_coeff_mag", 0.90))
    gamma_phase = math.radians(float(controls.get("inox_reflection_phase_deg", 180.0)))
    gamma = gamma_mag * complex(math.cos(gamma_phase), math.sin(gamma_phase))
    max_boost = float(controls.get("inox_multipath_max_boost_db", 12.0))
    max_null = float(controls.get("inox_multipath_max_null_db", 25.0))

    p_ant = arr(ant["position"])
    n_ant = norm_vec(ant["normal"])
    d0 = max(float(direct_distance_m), 1e-5)
    g0_lin = db_to_lin(direct_gain_eff_dbi)
    e_direct = math.sqrt(max(g0_lin, EPS)) * complex(math.cos(-k*d0), math.sin(-k*d0)) / d0
    e_sum = e_direct
    n_paths = 0

    for panel in scene.get("cabin", {}).get("panels", []):
        if not is_reflective_panel(panel, scene, controls):
            continue
        p_img = reflect_point_across_panel(p_ant, panel)
        p_ref = line_intersection_with_panel_plane(p_img, point, panel)
        if p_ref is None or not point_inside_panel_span(p_ref, panel):
            continue
        # Direção que sai da antena real até o ponto de reflexão. Isso aproxima
        # se a reflexão está dentro do lóbulo irradiado pela antena.
        v_ref = p_ref - p_ant
        d_ref_from_ant = float(np.linalg.norm(v_ref))
        if d_ref_from_ant < 1e-5:
            continue
        u_ref = v_ref / d_ref_from_ant
        angle_ref = math.degrees(math.acos(float(np.clip(np.dot(n_ant, u_ref), -1.0, 1.0))))
        g_ref = antenna_pattern_gain_db(
            peak_gain_dbi=float(ant.get("gain_dbi", controls["reader_antenna_gain_dbi"])),
            angle_deg=angle_ref,
            hpbw_deg=float(ant.get("hpbw_deg", controls["antenna_hpbw_deg"])),
            front_to_back_db=controls["antenna_front_to_back_db"],
        )
        d_img = max(float(np.linalg.norm(point - p_img)), 1e-5)
        e_ref = gamma * math.sqrt(max(db_to_lin(g_ref), EPS)) * complex(math.cos(-k*d_img), math.sin(-k*d_img)) / d_img
        e_sum += e_ref
        n_paths += 1

    if n_paths == 0:
        return {"inox_multipath_delta_db": 0.0, "inox_multipath_loss_db": 0.0, "inox_reflection_paths": 0, "inox_multipath_note": "sem_reflexoes_validas"}

    ratio = abs(e_sum) / max(abs(e_direct), EPS)
    delta_db = 20.0 * math.log10(max(ratio, EPS))
    delta_db = max(-max_null, min(max_boost, delta_db))
    # Para o link budget, um delta positivo é ganho por soma construtiva;
    # um delta negativo vira perda adicional por cancelamento.
    loss_db = -delta_db if controls.get("apply_inox_multipath_to_link", 0.0) > 0.5 else 0.0
    note = "aplicado_no_link" if controls.get("apply_inox_multipath_to_link", 0.0) > 0.5 else "diagnostico_sem_aplicar"
    return {
        "inox_multipath_delta_db": float(delta_db),
        "inox_multipath_loss_db": float(loss_db),
        "inox_reflection_paths": int(n_paths),
        "inox_multipath_note": note,
    }

def min_distance_to_reflective_panel(point: np.ndarray, scene: Dict[str, Any], controls: Dict[str, float]) -> Tuple[float, str]:
    best_d = float("inf")
    best_name = ""
    for panel in scene.get("cabin", {}).get("panels", []):
        if not is_reflective_panel(panel, scene, controls):
            continue
        plane = panel.get("plane")
        coord = float(panel.get("coord", 0.0))
        idx = {"x": 0, "y": 1, "z": 2}.get(plane, 0)
        # distância perpendicular; só marca painel se a projeção cair no span
        proj = np.array(point, dtype=float).copy(); proj[idx] = coord
        if point_inside_panel_span(proj, panel):
            d = abs(float(point[idx] - coord))
            if d < best_d:
                best_d = d; best_name = str(panel.get("name", panel.get("material", "painel")))
    if not math.isfinite(best_d):
        return float("nan"), "sem_painel_refletivo_proximo"
    return best_d, best_name

def vswr_risk_rows(scene: Dict[str, Any], controls: Dict[str, float]) -> pd.DataFrame:
    """Indicador geométrico de risco de VSWR/S11. Não calcula VSWR real."""
    lam = wavelength(controls["frequency_hz"])
    rows = []
    for ant in scene.get("antennas", []):
        p = arr(ant["position"])
        d, panel_name = min_distance_to_reflective_panel(p, scene, controls)
        if not math.isfinite(d):
            risk = "NÃO AVALIADO"
            obs = "nenhum painel metálico/refletivo detectado no modelo"
            d_lam = float("nan")
        else:
            d_lam = d / max(lam, EPS)
            if d < lam / 8.0:
                risk = "ALTO"
                obs = "antena muito próxima de metal (< λ/8); medir S11/VSWR obrigatoriamente"
            elif d < lam / 4.0:
                risk = "MÉDIO/ALTO"
                obs = "antena próxima de metal (< λ/4); possível alteração de impedância e padrão"
            elif d < lam / 2.0:
                risk = "MÉDIO"
                obs = "metal no campo próximo relativo; validar com VNA se possível"
            else:
                risk = "BAIXO"
                obs = "distância geométrica menos crítica, mas VSWR ainda depende da antena real"
        rows.append({
            "antena": ant.get("name", "ANT"),
            "x_m": round(float(p[0]), 4),
            "y_m": round(float(p[1]), 4),
            "z_m": round(float(p[2]), 4),
            "painel_refletivo_mais_proximo": panel_name,
            "distancia_ao_metal_m": None if not math.isfinite(d) else round(d, 4),
            "distancia_em_lambdas": None if not math.isfinite(d_lam) else round(d_lam, 3),
            "lambda_m": round(lam, 4),
            "lambda_quarto_m": round(lam/4.0, 4),
            "risco_vswr_s11": risk,
            "observacao": obs,
            "importante": "Este é só um indicador geométrico. VSWR real exige VNA/medidor de potência refletida.",
        })
    return pd.DataFrame(rows)

def multipath_tag_rows(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    rows = []
    # Calcula duas vezes: sem aplicar e aplicando, para mostrar o impacto estimado.
    c_diag = dict(controls); c_diag["use_inox_multipath"] = 1.0; c_diag["apply_inox_multipath_to_link"] = 0.0
    c_apply = dict(controls); c_apply["use_inox_multipath"] = 1.0; c_apply["apply_inox_multipath_to_link"] = 1.0
    for tag in scene.get("tags", []):
        p = arr(tag["position"])
        base = compute_best_link(p, scene, {**controls, "use_inox_multipath": 0.0})
        diag = compute_best_link(p, scene, c_diag)
        applied = compute_best_link(p, scene, c_apply)
        rows.append({
            "tag": tag.get("name", "TAG"),
            "esperada_interna": bool(tag.get("inside_expected", True)),
            "antena_base": base["antenna"],
            "margem_sem_multipercurso_db": round(base["link_margin_db"], 3),
            "delta_multipercurso_primeira_ordem_db": round(diag.get("inox_multipath_delta_db", 0.0), 3),
            "reflexoes_validas": int(diag.get("inox_reflection_paths", 0)),
            "margem_com_multipercurso_aprox_db": round(applied["link_margin_db"], 3),
            "variacao_margem_db": round(applied["link_margin_db"] - base["link_margin_db"], 3),
            "status_sem": classify_margin(base["link_margin_db"], reliable_margin_db),
            "status_com_aprox": classify_margin(applied["link_margin_db"], reliable_margin_db),
            "observacao": "Aproximação por método das imagens; validar com bancada/openEMS. Não calcula modos completos de cavidade.",
        })
    return pd.DataFrame(rows)

def robustness_jitter_rows(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    """Testa se pequenas variações de posição geram queda brusca de margem.

    Isso não substitui multipercurso full-wave; é um teste operacional de robustez:
    se a tag só lê em um ponto exato, a instalação é frágil.
    """
    radius = float(controls.get("robustness_jitter_radius_m", 0.05))
    n_axis = int(controls.get("robustness_grid_per_axis", 3))
    n_axis = max(3, min(5, n_axis))
    offsets_1d = np.linspace(-radius, radius, n_axis)
    offsets = []
    for dx in offsets_1d:
        for dy in offsets_1d:
            for dz in offsets_1d:
                if math.sqrt(dx*dx+dy*dy+dz*dz) <= radius * 1.001:
                    offsets.append(np.array([dx,dy,dz], dtype=float))
    rows = []
    for tag in scene.get("tags", []):
        if not bool(tag.get("inside_expected", True)):
            continue
        p0 = arr(tag["position"])
        margins = []
        antennas = []
        for off in offsets:
            p = p0 + off
            # Evita pontos negativos abaixo da balança/piso.
            if p[2] < 0.02:
                continue
            r = compute_best_link(p, scene, controls)
            margins.append(float(r["link_margin_db"]))
            antennas.append(r["antenna"])
        if not margins:
            continue
        margins_np = np.array(margins, dtype=float)
        fail_count = int((margins_np < 0.0).sum())
        marginal_count = int(((margins_np >= 0.0) & (margins_np < reliable_margin_db)).sum())
        if fail_count > 0:
            risk = "ALTO: pequena variação cria zona morta"
        elif marginal_count > 0:
            risk = "MÉDIO: pequena variação cria leitura marginal"
        elif float(np.std(margins_np)) > 6.0:
            risk = "MÉDIO: margem varia muito"
        else:
            risk = "BAIXO"
        rows.append({
            "tag": tag.get("name", "TAG"),
            "x_m": round(float(p0[0]), 4),
            "y_m": round(float(p0[1]), 4),
            "z_m": round(float(p0[2]), 4),
            "raio_teste_m": round(radius, 3),
            "pontos_testados": int(len(margins)),
            "margem_nominal_db": round(float(compute_best_link(p0, scene, controls)["link_margin_db"]), 3),
            "margem_min_db": round(float(np.min(margins_np)), 3),
            "margem_media_db": round(float(np.mean(margins_np)), 3),
            "margem_std_db": round(float(np.std(margins_np)), 3),
            "pontos_falha": fail_count,
            "pontos_marginais": marginal_count,
            "antenas_mais_usadas": ", ".join(pd.Series(antennas).value_counts().head(3).index.astype(str).tolist()),
            "risco_robustez": risk,
        })
    return pd.DataFrame(rows)

def compute_link_for_antenna(
    ant: Dict[str, Any],
    point: np.ndarray,
    scene: Dict[str, Any],
    controls: Dict[str, float],
) -> Dict[str, Any]:
    effects = compute_path_effects(ant, point, scene, controls)
    rf = scene["rf"]

    p_tx = controls["reader_tx_power_dbm"]
    cable = controls["cable_loss_db"]
    g_tag = controls["tag_gain_dbi"]
    pol_loss = controls["polarization_loss_db"]
    orient_loss = controls["tag_orientation_extra_loss_db"]
    backscatter = controls["backscatter_link_loss_db"]

    path_one_way = (
        effects["fspl_db"]
        + effects["total_medium_loss_db"]
        + pol_loss
        + orient_loss
    )

    # Forward link: leitor -> tag. A tag precisa ligar.
    p_tag_dbm = (
        p_tx
        - cable
        + effects["reader_gain_dbi_eff"]
        + g_tag
        - path_one_way
    )

    # Reverse link: tag -> leitor por backscatter. Sofre ida e volta.
    # Modelo analítico simplificado de radar/backscatter monostático.
    p_rx_dbm = (
        p_tx
        - 2.0 * cable
        + 2.0 * effects["reader_gain_dbi_eff"]
        + 2.0 * g_tag
        - 2.0 * path_one_way
        - backscatter
    )

    f_margin = p_tag_dbm - controls["tag_activation_dbm"]
    r_margin = p_rx_dbm - controls["reader_sensitivity_dbm"]
    link_margin = min(f_margin, r_margin)
    read_ok = f_margin >= 0.0 and r_margin >= 0.0

    return {
        **effects,
        "antenna": ant.get("name", "ANT"),
        "p_tag_dbm": p_tag_dbm,
        "p_rx_dbm": p_rx_dbm,
        "forward_margin_db": f_margin,
        "reverse_margin_db": r_margin,
        "link_margin_db": link_margin,
        "read_ok": read_ok,
    }

def compute_best_link(point: np.ndarray, scene: Dict[str, Any], controls: Dict[str, float]) -> Dict[str, Any]:
    results = [compute_link_for_antenna(ant, point, scene, controls) for ant in scene.get("antennas", [])]
    if not results:
        raise RuntimeError("Nenhuma antena definida na cena.")
    return max(results, key=lambda r: r["link_margin_db"])

def classify_margin(margin_db: float, reliable_margin_db: float) -> str:
    if margin_db >= reliable_margin_db:
        return "LEITURA CONFIÁVEL"
    if margin_db >= 0.0:
        return "LEITURA MARGINAL"
    return "ZONA MORTA"

# Diagnóstico e exportação

def classify_link_bottleneck(link: Dict[str, Any], reliable_margin_db: float) -> str:
    """Classifica a causa imediata da falha pelo menor elo do link budget."""
    fm = float(link["forward_margin_db"])
    rm = float(link["reverse_margin_db"])
    lm = float(link["link_margin_db"])
    if fm < 0.0 and rm < 0.0:
        return "FALHA_FORWARD_E_REVERSE"
    if fm < 0.0:
        return "FALHA_FORWARD_TAG_NAO_ATIVA"
    if rm < 0.0:
        return "FALHA_REVERSE_LEITOR_NAO_OUVE"
    if lm < reliable_margin_db:
        return "LEITURA_MARGINAL_SEM_FOLGA"
    return "LEITURA_CONFIAVEL"

def dominant_loss_terms(link: Dict[str, Any], controls: Dict[str, float], top_n: int = 4) -> str:
    """Retorna os termos de perda mais relevantes para explicar a margem."""
    angular_loss = max(0.0, float(controls["reader_antenna_gain_dbi"]) - float(link["reader_gain_dbi_eff"]))
    terms = {
        "FSPL/distância": float(link.get("fspl_db", 0.0)),
        "perda angular antena": angular_loss,
        "tecido/enxoval": float(link.get("textile_loss_db", 0.0)),
        "gaiola/grade": float(link.get("cage_loss_db", 0.0)),
        "cabine/painéis": float(link.get("cabin_loss_db", 0.0)),
        "multipercurso balança": float(link.get("multipath_penalty_db", 0.0)),
        "multipercurso Inox aprox.": max(0.0, float(link.get("inox_multipath_loss_db", 0.0))),
        "polarização": float(controls.get("polarization_loss_db", 0.0)),
        "orientação/dobra": float(controls.get("tag_orientation_extra_loss_db", 0.0)),
        "backscatter": float(controls.get("backscatter_link_loss_db", 0.0)),
    }
    # FSPL e backscatter quase sempre aparecem grandes; a intenção é mostrar peso, não culpar isoladamente.
    items = sorted(terms.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return "; ".join([f"{k}: {v:.1f} dB" for k, v in items])

def probable_action(link: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> str:
    """Sugere ação física ou calibração com base nos termos do link budget."""
    bottleneck = classify_link_bottleneck(link, reliable_margin_db)
    angle = float(link.get("angle_deg", 0.0))
    textile = float(link.get("textile_loss_db", 0.0))
    angular_loss = max(0.0, float(controls["reader_antenna_gain_dbi"]) - float(link["reader_gain_dbi_eff"]))
    cage = float(link.get("cage_loss_db", 0.0))
    cab = float(link.get("cabin_loss_db", 0.0))
    mult = float(link.get("multipath_penalty_db", 0.0))
    inox_delta = float(link.get("inox_multipath_delta_db", 0.0))

    suggestions = []
    if bottleneck == "FALHA_FORWARD_TAG_NAO_ATIVA":
        suggestions.append("verificar energização da tag: EIRP, ganho efetivo, ângulo, tecido e distância")
    elif bottleneck == "FALHA_REVERSE_LEITOR_NAO_OUVE":
        suggestions.append("gargalo no retorno: comparar P_rx/RSSI com sensibilidade do leitor e calibrar backscatter")
    elif bottleneck == "LEITURA_MARGINAL_SEM_FOLGA":
        suggestions.append("marginal: buscar +6 dB de folga para robustez")
    else:
        suggestions.append("sem falha imediata; validar em bancada por taxa de leitura")

    if angle > 50 or angular_loss > 3:
        suggestions.append("melhorar geometria: inclinar/rebaixar/adicionar antena; tag fora do lóbulo útil")
    if textile > 4:
        suggestions.append("avaliar tag soterrada: medir atenuação do tecido seco/úmido em bancada")
    if cage > 2:
        suggestions.append("verificar perda equivalente da grade/gaiola por cruzamento")
    if cab > 5:
        suggestions.append("verificar se caminho atravessa painéis da cabine indevidamente")
    if mult > 1:
        suggestions.append("testar afastamento da balança/efeito multipercurso")
    if abs(inox_delta) >= 6:
        suggestions.append("cabine metálica: possível pico/vale por reflexão; validar com deslocamento ±5 cm ou openEMS")
    if controls.get("polarization_loss_db", 0) >= 3:
        suggestions.append("testar perda de polarização: antena CP × tag linear pode estar conservadora")
    return " | ".join(suggestions)

def diagnostic_tag_rows(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    """Tabela completa por tag/probe usando a melhor antena."""
    rows = []
    for tag in scene.get("tags", []):
        p = arr(tag["position"])
        best = compute_best_link(p, scene, controls)
        expected_inside = bool(tag.get("inside_expected", True))
        path_one_way = (
            best["fspl_db"] + best["total_medium_loss_db"]
            + controls["polarization_loss_db"] + controls["tag_orientation_extra_loss_db"]
        )
        angular_loss = max(0.0, controls["reader_antenna_gain_dbi"] - best["reader_gain_dbi_eff"])
        status = classify_margin(best["link_margin_db"], reliable_margin_db)
        if not expected_inside and best["read_ok"]:
            status = "VAZAMENTO / LEITURA INDEVIDA"
        rows.append({
            "tag": tag.get("name", "TAG"),
            "esperada_interna": expected_inside,
            "x_m": round(float(p[0]), 4),
            "y_m": round(float(p[1]), 4),
            "z_m": round(float(p[2]), 4),
            "melhor_antena": best["antenna"],
            "status": status,
            "gargalo": classify_link_bottleneck(best, reliable_margin_db),
            "p_tag_dbm": round(best["p_tag_dbm"], 3),
            "margem_ida_db": round(best["forward_margin_db"], 3),
            "rssi_reverso_estimado_p_rx_dbm": round(best["p_rx_dbm"], 3),
            "margem_volta_db": round(best["reverse_margin_db"], 3),
            "margem_final_db": round(best["link_margin_db"], 3),
            "distancia_m": round(best["distance_m"], 4),
            "angulo_graus": round(best["angle_deg"], 3),
            "ganho_antena_efetivo_dbi": round(best["reader_gain_dbi_eff"], 3),
            "perda_angular_db": round(angular_loss, 3),
            "fspl_db": round(best["fspl_db"], 3),
            "perda_cabine_db": round(best["cabin_loss_db"], 3),
            "paineis_cruzados": ", ".join(best.get("crossed_panels", [])),
            "perda_gaiola_db": round(best["cage_loss_db"], 3),
            "cruzamentos_gaiola": best.get("cage_crossings", 0),
            "comprimento_tecido_m": round(best["textile_len_m"], 4),
            "perda_tecido_db": round(best["textile_loss_db"], 3),
            "perda_multipercurso_balanca_db": round(best["multipath_penalty_db"], 3),
            "delta_multipercurso_inox_db": round(float(best.get("inox_multipath_delta_db", 0.0)), 3),
            "perda_multipercurso_inox_aplicada_db": round(float(best.get("inox_multipath_loss_db", 0.0)), 3),
            "reflexoes_inox_primeira_ordem": int(best.get("inox_reflection_paths", 0)),
            "perda_polarizacao_db": round(float(controls["polarization_loss_db"]), 3),
            "perda_orientacao_db": round(float(controls["tag_orientation_extra_loss_db"]), 3),
            "perda_backscatter_db": round(float(controls["backscatter_link_loss_db"]), 3),
            "perda_cabo_db": round(float(controls["cable_loss_db"]), 3),
            "ganho_tag_dbi": round(float(controls["tag_gain_dbi"]), 3),
            "path_one_way_db": round(path_one_way, 3),
            "campo_proximo": bool(best["near_field"]),
            "perdas_dominantes": dominant_loss_terms(best, controls),
            "acao_recomendada": probable_action(best, controls, reliable_margin_db),
        })
    return pd.DataFrame(rows)

def diagnostic_antenna_rows(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    """Tabela tag × antena, útil para descobrir se o problema é geometria/ângulo."""
    rows = []
    for tag in scene.get("tags", []):
        p = arr(tag["position"])
        for ant in scene.get("antennas", []):
            r = compute_link_for_antenna(ant, p, scene, controls)
            rows.append({
                "tag": tag.get("name", "TAG"),
                "esperada_interna": bool(tag.get("inside_expected", True)),
                "antena": ant.get("name", "ANT"),
                "read_ok": bool(r["read_ok"]),
                "classificacao": classify_link_bottleneck(r, reliable_margin_db),
                "margem_final_db": round(r["link_margin_db"], 3),
                "margem_ida_db": round(r["forward_margin_db"], 3),
                "margem_volta_db": round(r["reverse_margin_db"], 3),
                "p_tag_dbm": round(r["p_tag_dbm"], 3),
                "p_rx_dbm": round(r["p_rx_dbm"], 3),
                "distancia_m": round(r["distance_m"], 4),
                "angulo_graus": round(r["angle_deg"], 3),
                "ganho_antena_efetivo_dbi": round(r["reader_gain_dbi_eff"], 3),
                "fspl_db": round(r["fspl_db"], 3),
                "perda_tecido_db": round(r["textile_loss_db"], 3),
                "perda_gaiola_db": round(r["cage_loss_db"], 3),
                "perda_cabine_db": round(r["cabin_loss_db"], 3),
                "perda_multipercurso_db": round(r["multipath_penalty_db"], 3),
                "delta_multipercurso_inox_db": round(float(r.get("inox_multipath_delta_db", 0.0)), 3),
                "perda_multipercurso_inox_aplicada_db": round(float(r.get("inox_multipath_loss_db", 0.0)), 3),
                "reflexoes_inox_primeira_ordem": int(r.get("inox_reflection_paths", 0)),
            })
    return pd.DataFrame(rows)

def diagnostic_ablation_rows(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    """Testes de ablação: muda um parâmetro por vez para descobrir o termo suspeito."""
    variants = []
    variants.append(("baseline", "sem alteração", {}))
    variants.append(("sem_tecido", "desliga atenuação do tecido", {"use_textile_loss": 0.0}))
    variants.append(("tecido_50pct", "reduz atenuação do tecido pela metade", {"textile_attenuation_db_per_m": controls["textile_attenuation_db_per_m"] * 0.5}))
    variants.append(("sem_gaiola", "desliga perda equivalente da grade", {"use_cage_loss": 0.0}))
    variants.append(("sem_polarizacao", "remove perda de polarização", {"polarization_loss_db": 0.0}))
    variants.append(("sem_orientacao", "remove perda extra de orientação/dobra", {"tag_orientation_extra_loss_db": 0.0}))
    variants.append(("backscatter_menos_3dB", "reduz perda de backscatter em 3 dB", {"backscatter_link_loss_db": max(0.0, controls["backscatter_link_loss_db"] - 3.0)}))
    variants.append(("leitor_2dB_mais_sensivel", "melhora sensibilidade do leitor em 2 dB", {"reader_sensitivity_dbm": controls["reader_sensitivity_dbm"] - 2.0}))
    variants.append(("tag_mais_2dB", "aumenta ganho efetivo da tag em 2 dB", {"tag_gain_dbi": controls["tag_gain_dbi"] + 2.0}))
    variants.append(("beamwidth_90graus", "abre HPBW para 90°", {"antenna_hpbw_deg": max(90.0, controls["antenna_hpbw_deg"])}))
    variants.append(("sem_multipercurso_balanca", "remove penalidade de multipercurso da balança", {"use_scale_multipath": 0.0}))

    baseline = {}
    for tag in scene.get("tags", []):
        baseline[tag.get("name", "TAG")] = compute_best_link(arr(tag["position"]), scene, controls)

    rows = []
    for tag in scene.get("tags", []):
        name = tag.get("name", "TAG")
        p = arr(tag["position"])
        base = baseline[name]
        for variant_name, descricao, updates in variants:
            c = dict(controls)
            c.update(updates)
            r = compute_best_link(p, scene, c)
            passou_antes = bool(base["read_ok"])
            passou_depois = bool(r["read_ok"])
            rows.append({
                "tag": name,
                "esperada_interna": bool(tag.get("inside_expected", True)),
                "variante": variant_name,
                "descricao": descricao,
                "antena": r["antenna"],
                "margem_final_baseline_db": round(base["link_margin_db"], 3),
                "margem_final_variante_db": round(r["link_margin_db"], 3),
                "delta_margem_db": round(r["link_margin_db"] - base["link_margin_db"], 3),
                "margem_ida_db": round(r["forward_margin_db"], 3),
                "margem_volta_db": round(r["reverse_margin_db"], 3),
                "passou_baseline": passou_antes,
                "passou_variante": passou_depois,
                "resolveu_falha": (not passou_antes) and passou_depois,
                "classificacao": classify_link_bottleneck(r, reliable_margin_db),
            })
    return pd.DataFrame(rows)

def diagnostic_summary_df(df_diag: pd.DataFrame, df_ablation: pd.DataFrame, controls: Dict[str, float], reliable_margin_db: float) -> pd.DataFrame:
    """Resumo executivo para interpretação rápida."""
    internal = df_diag[df_diag["esperada_interna"] == True]
    external = df_diag[df_diag["esperada_interna"] == False]
    n_int = len(internal)
    n_ext = len(external)
    read_int = int((internal["margem_final_db"] >= 0).sum()) if n_int else 0
    reliable_int = int((internal["margem_final_db"] >= reliable_margin_db).sum()) if n_int else 0
    leak_ext = int((external["margem_final_db"] >= 0).sum()) if n_ext else 0
    bottlenecks = df_diag["gargalo"].value_counts().to_dict() if not df_diag.empty else {}
    solved = df_ablation[df_ablation["resolveu_falha"] == True]
    top_solutions = solved.groupby("variante").size().sort_values(ascending=False).head(8).to_dict() if not solved.empty else {}
    rows = [
        {"indicador": "tags_internas_lidas", "valor": read_int, "observacao": f"de {n_int}"},
        {"indicador": "tags_internas_confiaveis", "valor": reliable_int, "observacao": f"margem >= {reliable_margin_db:.1f} dB"},
        {"indicador": "probes_externos_lidos_vazamento", "valor": leak_ext, "observacao": f"de {n_ext}"},
        {"indicador": "EIRP_dbm", "valor": round(controls.get("eirp_limit_dbm", 0.0), 3), "observacao": "potência irradiada efetiva"},
        {"indicador": "P_leitor_dbm", "valor": round(controls.get("reader_tx_power_dbm", 0.0), 3), "observacao": "potência conduzida"},
        {"indicador": "sensibilidade_leitor_dbm", "valor": round(controls.get("reader_sensitivity_dbm", 0.0), 3), "observacao": "reverse link"},
        {"indicador": "ativacao_tag_dbm", "valor": round(controls.get("tag_activation_dbm", 0.0), 3), "observacao": "forward link"},
        {"indicador": "backscatter_loss_db", "valor": round(controls.get("backscatter_link_loss_db", 0.0), 3), "observacao": "calibrar com RSSI real"},
        {"indicador": "bottlenecks", "valor": json.dumps(bottlenecks, ensure_ascii=False), "observacao": "contagem por gargalo"},
        {"indicador": "ablacoes_que_resolveram", "valor": json.dumps(top_solutions, ensure_ascii=False), "observacao": "quais mudanças fizeram tag falha passar"},
    ]
    return pd.DataFrame(rows)

def controls_df(controls: Dict[str, float], scene_source: str, reliable_margin_db: float) -> pd.DataFrame:
    items = []
    for k, v in controls.items():
        items.append({"parametro": k, "valor": v})
    items.append({"parametro": "scene_source", "valor": scene_source})
    items.append({"parametro": "reliable_margin_db", "valor": reliable_margin_db})
    return pd.DataFrame(items)

def build_diagnostic_workbook_bytes(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float, scene_source: str) -> bytes:
    """Exporta o diagnóstico em XLSX."""
    df_diag = diagnostic_tag_rows(scene, controls, reliable_margin_db)
    df_ant = diagnostic_antenna_rows(scene, controls, reliable_margin_db)
    df_ablation = diagnostic_ablation_rows(scene, controls, reliable_margin_db)
    df_summary = diagnostic_summary_df(df_diag, df_ablation, controls, reliable_margin_db)
    df_ctrl = controls_df(controls, scene_source, reliable_margin_db)
    df_mp = multipath_tag_rows(scene, controls, reliable_margin_db)
    df_rob = robustness_jitter_rows(scene, controls, reliable_margin_db)
    df_vswr = vswr_risk_rows(scene, controls)

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df_summary.to_excel(writer, sheet_name="00_resumo", index=False)
        df_diag.to_excel(writer, sheet_name="01_tags_diagnostico", index=False)
        df_ant.to_excel(writer, sheet_name="02_tag_por_antena", index=False)
        df_ablation.to_excel(writer, sheet_name="03_ablacao", index=False)
        df_ctrl.to_excel(writer, sheet_name="04_parametros", index=False)
        df_mp.to_excel(writer, sheet_name="05_multipercurso_inox", index=False)
        df_rob.to_excel(writer, sheet_name="06_robustez_posicao", index=False)
        df_vswr.to_excel(writer, sheet_name="07_risco_vswr", index=False)

        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1, "text_wrap": True})
        warn_fmt = workbook.add_format({"bg_color": "#FFF2CC"})
        bad_fmt = workbook.add_format({"bg_color": "#F4CCCC"})
        good_fmt = workbook.add_format({"bg_color": "#D9EAD3"})
        num_fmt = workbook.add_format({"num_format": "0.00"})
        for sheet_name, df in {
            "00_resumo": df_summary,
            "01_tags_diagnostico": df_diag,
            "02_tag_por_antena": df_ant,
            "03_ablacao": df_ablation,
            "04_parametros": df_ctrl,
            "05_multipercurso_inox": df_mp,
            "06_robustez_posicao": df_rob,
            "07_risco_vswr": df_vswr,
        }.items():
            ws = writer.sheets[sheet_name]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
            for col_num, value in enumerate(df.columns.values):
                ws.write(0, col_num, value, header_fmt)
                width = min(max(12, len(str(value)) + 2), 42)
                ws.set_column(col_num, col_num, width)
            # formatação de colunas de margem quando presentes
            for col_name in df.columns:
                if "margem" in col_name or col_name.endswith("_db") or "dbm" in col_name:
                    idx = list(df.columns).index(col_name)
                    ws.set_column(idx, idx, 14, num_fmt)
                    if "margem" in col_name:
                        ws.conditional_format(1, idx, max(len(df), 1), idx, {"type": "cell", "criteria": "<", "value": 0, "format": bad_fmt})
                        ws.conditional_format(1, idx, max(len(df), 1), idx, {"type": "cell", "criteria": "between", "minimum": 0, "maximum": reliable_margin_db, "format": warn_fmt})
                        ws.conditional_format(1, idx, max(len(df), 1), idx, {"type": "cell", "criteria": ">=", "value": reliable_margin_db, "format": good_fmt})
    bio.seek(0)
    return bio.getvalue()

def build_diagnostic_csv_zip_bytes(scene: Dict[str, Any], controls: Dict[str, float], reliable_margin_db: float, scene_source: str) -> bytes:
    """Exporta ZIP/CSV quando XLSX não estiver disponível."""
    df_diag = diagnostic_tag_rows(scene, controls, reliable_margin_db)
    df_ant = diagnostic_antenna_rows(scene, controls, reliable_margin_db)
    df_ablation = diagnostic_ablation_rows(scene, controls, reliable_margin_db)
    df_summary = diagnostic_summary_df(df_diag, df_ablation, controls, reliable_margin_db)
    df_ctrl = controls_df(controls, scene_source, reliable_margin_db)
    df_mp = multipath_tag_rows(scene, controls, reliable_margin_db)
    df_rob = robustness_jitter_rows(scene, controls, reliable_margin_db)
    df_vswr = vswr_risk_rows(scene, controls)
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, df in [
            ("00_resumo.csv", df_summary),
            ("01_tags_diagnostico.csv", df_diag),
            ("02_tag_por_antena.csv", df_ant),
            ("03_ablacao.csv", df_ablation),
            ("04_parametros.csv", df_ctrl),
            ("05_multipercurso_inox.csv", df_mp),
            ("06_robustez_posicao.csv", df_rob),
            ("07_risco_vswr.csv", df_vswr),
        ]:
            zf.writestr(name, df.to_csv(index=False).encode("utf-8-sig"))
    bio.seek(0)
    return bio.getvalue()

# Interface

st.set_page_config(page_title="Raio X RFID UHF Hospitalar", page_icon="📡", layout="wide")
st.title("📡 Raio X Analítico — Portal RFID UHF Hospitalar v7")
st.caption("Modelo físico por camadas com interface normal para apresentação e modo avançado para calibração.")

# Carregamento do JSON de cena
scene_source = "Cena padrão interna"
scene = default_scene()
json_default = find_default_json()

with st.sidebar:
    st.header("📁 Cena física")
    uploaded_json = st.file_uploader("Carregar rfid_scene_metadata.json", type=["json"])
    if uploaded_json is not None:
        scene = json.loads(uploaded_json.getvalue().decode("utf-8"))
        scene_source = uploaded_json.name
    elif json_default is not None:
        try:
            scene = load_scene_from_json(json_default)
            scene_source = str(json_default)
        except Exception as exc:
            st.warning(f"Falha ao ler JSON local: {exc}. Usando cena padrão.")

st.info(f"Cena em uso: **{scene_source}**")

rf = scene.get("rf", default_scene()["rf"])
materials = scene.get("materials", default_scene()["materials"])

with st.sidebar:
    st.header("⚙️ Modo de uso")
    interface_mode = st.radio(
        "Interface",
        ["Normal — apresentação", "Avançado — calibração"],
        index=0,
        help=(
            "Use o modo Normal na reunião: ele mantém constantes físicas e parâmetros derivados "
            "calculados automaticamente. Use o modo Avançado apenas para calibração e ensaios."
        ),
    )
    show_advanced = interface_mode.startswith("Avançado")

    st.caption(
        "Fluxo do projeto: **Blender modela → App verifica analiticamente → "
        "openEMS avalia fenômenos 3D locais → Bancada valida e quantifica diferenças**."
    )
    st.success(
        "Perfil ativo: **Laird PAL90209H (LHCP), 9 dBic, HPBW 70°, 902-928 MHz**. "
        "A tag permanece aproximada e paramétrica (75 x 20 mm)."
    )

    st.header("🎛️ Cenário de análise")
    preset_name = st.selectbox(
        "Preset técnico",
        list(RF_PRESETS.keys()),
        index=0,
        help="Preset base para não deixar a apresentação parecendo uma escolha livre de parâmetros."
    )
    preset = RF_PRESETS[preset_name]

    if show_advanced:
        use_preset_defaults = st.checkbox(
            "Usar valores do preset como padrão",
            value=True,
            help=(
                "Quando marcado, os controles iniciam com a base física corrigida. "
                "Desmarque somente para auditar valores vindos do JSON."
            )
        )
    else:
        use_preset_defaults = True
        st.info(
            "Modo Normal ativo: apenas os controles essenciais ficam expostos. "
            "Parâmetros físicos derivados são calculados automaticamente e parâmetros empíricos ficam ocultos."
        )

    def rf_default(key: str, fallback: float) -> float:
        if use_preset_defaults and key in preset:
            return float(preset[key])
        return float(rf.get(key, fallback))

    # Valores base: no modo Normal ficam fixos/calculados; no Avançado ficam editáveis.

    freq_mhz = float(rf.get("frequency_hz", 915e6)) / 1e6
    power_mode = "Limite por EIRP (recomendado)"
    reader_antenna_gain_dbi = rf_default("reader_antenna_gain_dbi", 9.0)
    cable_loss_db = rf_default("cable_loss_db", 1.0)
    eirp_limit_dbm = rf_default("eirp_limit_dbm", 36.0)
    reader_tx_power_dbm = conducted_power_from_eirp(eirp_limit_dbm, reader_antenna_gain_dbi, cable_loss_db)
    tag_activation_dbm = rf_default("tag_activation_dbm", -18.0)
    reader_sensitivity_dbm = rf_default("reader_sensitivity_dbm", -90.0)
    tag_gain_dbi = rf_default("tag_gain_dbi", 0.0)
    backscatter_link_loss_db = rf_default("backscatter_link_loss_db", 28.0)

    polarization_loss_db = float(rf.get("polarization_loss_db", rf_default("polarization_loss_db", 3.0)))
    tag_orientation_extra_loss_db = float(rf.get("tag_orientation_extra_loss_db", rf_default("tag_orientation_extra_loss_db", 2.0)))
    antenna_hpbw_deg = float(rf.get("antenna_hpbw_deg", 70.0))
    antenna_front_to_back_db = float(rf.get("antenna_front_to_back_db", 20.0))
    antenna_largest_dimension_m = float(rf.get("antenna_largest_dimension_m", 0.2591))

    # Antenas: no modo Normal, usa a geometria que veio do Blender/JSON.
    edit_antennas_in_app = False
    ant_by_name = {a.get("name"): a for a in scene.get("antennas", [])}
    esq0 = ant_by_name.get("ESQ", {"position": [-0.525, -0.03, 1.08]})["position"]
    dir0 = ant_by_name.get("DIR", {"position": [0.525, -0.03, 1.08]})["position"]
    top0 = ant_by_name.get("TOPO", {"position": [0.0, -0.03, 2.015]})["position"]
    lateral_z = float((esq0[2] + dir0[2]) / 2.0)
    lateral_y = float((esq0[1] + dir0[1]) / 2.0)
    lateral_tilt_deg = 0.0
    lateral_yaw_deg = 0.0
    top_z = float(top0[2])
    top_tilt_x_deg = 0.0
    top_tilt_y_deg = 0.0
    add_lower_side_antennas = False
    lower_lateral_z = 0.70
    lower_lateral_tilt_deg = -10.0

    # Pilha/tags.
    tv0 = scene.get("textile_volume", {})
    tv_center0 = tv0.get("center", [0.0, 0.0, 0.92])
    tv_size0 = tv0.get("size", [0.55, 0.62, 1.20])
    use_generated_stack_tags = True
    n_stack_tags = 80
    n_buried_center_tags = 12
    tag_seed = 42
    tag_distribution = "Centro mais denso"
    center_concentration = 0.70
    stack_center_x = float(tv_center0[0])
    stack_center_y = float(tv_center0[1])
    stack_center_z = float(tv_center0[2])
    stack_size_x = float(tv_size0[0])
    stack_size_y = float(tv_size0[1])
    stack_size_z = float(tv_size0[2])

    # Materiais/perdas.
    material_names = list(materials.keys())
    default_mat = scene.get("cabin", {}).get("default_wall_material", material_names[0])
    default_idx = material_names.index(default_mat) if default_mat in material_names else 0
    inox_idx = next((i for i, name in enumerate(material_names) if "inox" in name.lower() or "aço" in name.lower() or "aco" in name.lower()), default_idx)
    selected_wall_material = material_names[inox_idx]
    override_wall_loss_db = float(materials[selected_wall_material].get("wall_crossing_loss_db", 0.0))
    use_cage_loss = True
    cage_extra_diffraction_loss_db = float(scene.get("cage", {}).get("extra_diffraction_loss_db", 1.5))
    use_textile_loss = True
    textile_mode = "Seco"
    textile = scene.get("textile_volume", {})
    textile_att_default = float(preset.get("textile_dry_db_per_m", textile.get("attenuation_db_per_m_dry", 12.0)))
    textile_attenuation_db_per_m = textile_att_default
    use_scale_multipath = True
    scale_multipath_penalty_db = float(scene.get("scale", {}).get("metal_reflection_penalty_db", 2.0))

    # Inox/multipercurso/robustez.
    use_inox_multipath = True
    apply_inox_multipath_to_link = False
    inox_reflection_coeff_mag = 0.90
    inox_reflection_phase_deg = 180.0
    inox_multipath_max_boost_db = 12.0
    inox_multipath_max_null_db = 25.0
    robustness_jitter_radius_cm = 5.0
    robustness_grid_per_axis = 3

    # Mapa.
    z_slice = 1.00
    grid_n = 55
    x_extent = 1.8
    y_min = -2.2
    y_max = 1.4
    show_vertical_map = True
    vertical_plane = "X-Z com Y fixo"
    vertical_fixed_y = 0.00
    vertical_fixed_x = 0.00
    z_min_map = 0.05
    z_max_map = 1.95
    reliable_margin_db = float(preset.get("reliable_margin_db", rf.get("reliable_margin_db", 6.0)))

    # Controles essenciais — visíveis no modo Normal.

    st.subheader("Essenciais")
    selected_wall_material = st.selectbox(
        "Material da cabine",
        material_names,
        index=material_names.index(selected_wall_material),
        help="No cenário de apresentação, use Aço Inox para avaliar confinamento lateral e abertura frontal."
    )
    override_wall_loss_db = float(materials[selected_wall_material].get("wall_crossing_loss_db", override_wall_loss_db))

    eirp_limit_dbm = st.slider(
        "EIRP alvo do conjunto (dBm)",
        10.0, 36.0, eirp_limit_dbm, 0.5,
        help="36 dBm = 4 W EIRP. A potência conduzida é calculada automaticamente."
    )
    reader_tx_power_dbm = conducted_power_from_eirp(eirp_limit_dbm, reader_antenna_gain_dbi, cable_loss_db)

    reader_sensitivity_dbm = st.slider(
        "Sensibilidade reversa do leitor (dBm)",
        -95.0, -75.0, reader_sensitivity_dbm, 1.0,
        help="Parâmetro usado para comparar com o RSSI reverso estimado."
    )

    textile_mode = st.radio(
        "Condição do enxoval",
        ["Seco", "Úmido"],
        horizontal=True,
        help="No modo Normal, a atenuação dB/m vem do preset técnico."
    )
    if textile_mode == "Seco":
        textile_attenuation_db_per_m = float(preset.get("textile_dry_db_per_m", textile.get("attenuation_db_per_m_dry", 12.0)))
    else:
        textile_attenuation_db_per_m = float(preset.get("textile_wet_db_per_m", textile.get("attenuation_db_per_m_wet", 25.0)))

    use_generated_stack_tags = st.checkbox(
        "Gerar cenário de pilha de enxoval",
        value=use_generated_stack_tags,
        help="Gera tags distribuídas no volume do enxoval e preserva probes externos."
    )
    if use_generated_stack_tags:
        n_stack_tags = st.slider("Tags aleatórias na pilha", 20, 300, n_stack_tags, 10)
        n_buried_center_tags = st.slider("Tags soterradas centrais", 0, 40, n_buried_center_tags, 2)

    use_inox_multipath = st.checkbox(
        "Mostrar diagnóstico de multipercurso e VSWR",
        value=use_inox_multipath,
        help="Mantém a análise como diagnóstico. Por padrão, não altera a margem principal."
    )
    robustness_jitter_radius_cm = st.slider("Robustez: deslocamento local das tags (cm)", 1.0, 10.0, robustness_jitter_radius_cm, 1.0)

    with st.expander("📌 Valores fixos/calculados no modo Normal", expanded=False):
        st.markdown(
            f"""
            - Frequência de referência: **{freq_mhz:.1f} MHz**
            - Ganho nominal da antena: **{reader_antenna_gain_dbi:.1f} dBi**
            - Perda de cabo: **{cable_loss_db:.1f} dB**
            - Potência conduzida calculada: **{reader_tx_power_dbm:.1f} dBm**
            - Ativação da tag: **{tag_activation_dbm:.1f} dBm**
            - Backscatter agregado: **{backscatter_link_loss_db:.1f} dB**
            - Polarização base CP–LP: **{polarization_loss_db:.1f} dB**
            - Orientação/dobra adicional: **{tag_orientation_extra_loss_db:.1f} dB**
            - Atenuação do enxoval: **{textile_attenuation_db_per_m:.1f} dB/m**
            - Margem confiável: **{reliable_margin_db:.1f} dB**
            """
        )

    # Modo avançado — parâmetros de calibração e auditoria.

    if show_advanced:
        st.markdown("---")
        st.subheader("Modo avançado")

        with st.expander("⚡ RF, potência e tag", expanded=False):
            freq_mhz = st.number_input("Frequência (MHz)", 860.0, 960.0, freq_mhz, 1.0)
            power_mode = st.radio(
                "Modo de potência",
                ["Limite por EIRP (recomendado)", "Potência conduzida do leitor"],
                index=0,
            )
            reader_antenna_gain_dbi = st.slider("Ganho nominal da antena leitora (dBi)", 0.0, 15.0, reader_antenna_gain_dbi, 0.5)
            cable_loss_db = st.slider("Perda de cabo/conectores por caminho (dB)", 0.0, 5.0, cable_loss_db, 0.1)
            if power_mode == "Limite por EIRP (recomendado)":
                eirp_limit_dbm = st.slider("EIRP alvo do conjunto (dBm) — avançado", 10.0, 36.0, eirp_limit_dbm, 0.5)
                reader_tx_power_dbm = conducted_power_from_eirp(eirp_limit_dbm, reader_antenna_gain_dbi, cable_loss_db)
                st.caption(f"P_leitor calculado: **{reader_tx_power_dbm:.1f} dBm** ({dbm_to_watts(reader_tx_power_dbm):.3f} W)")
            else:
                reader_tx_power_dbm = st.slider("Potência conduzida do leitor (dBm)", 0.0, 33.0, float(rf.get("reader_tx_power_dbm", 28.0)), 1.0)
                eirp_limit_dbm = reader_tx_power_dbm - cable_loss_db + reader_antenna_gain_dbi
                st.caption(f"EIRP resultante: **{eirp_limit_dbm:.1f} dBm** ({dbm_to_watts(eirp_limit_dbm):.2f} W)")
            tag_activation_dbm = st.slider("Limiar de ativação da tag — forward link (dBm)", -25.0, -12.0, tag_activation_dbm, 0.5)
            reader_sensitivity_dbm = st.slider("Sensibilidade do leitor — reverse link (dBm)", -95.0, -55.0, reader_sensitivity_dbm, 1.0)
            tag_gain_dbi = st.slider("Ganho efetivo da tag costurada (dBi)", -8.0, 3.0, tag_gain_dbi, 0.5)
            backscatter_link_loss_db = st.slider("Perda de backscatter/modulação da tag (dB)", 20.0, 50.0, backscatter_link_loss_db, 1.0)

        with st.expander("🧭 Antena, polarização e geometria", expanded=False):
            polarization_loss_db = st.slider("Perda por polarização (dB)", 0.0, 10.0, polarization_loss_db, 0.5)
            tag_orientation_extra_loss_db = st.slider("Perda adicional por dobra/orientação da tag (dB)", 0.0, 15.0, tag_orientation_extra_loss_db, 0.5)
            antenna_hpbw_deg = st.slider("HPBW / abertura da antena (graus)", 30.0, 120.0, antenna_hpbw_deg, 1.0)
            antenna_front_to_back_db = st.slider("Relação frente-costas aproximada (dB)", 10.0, 35.0, antenna_front_to_back_db, 1.0)
            antenna_largest_dimension_m = st.number_input("Maior dimensão da antena (m)", 0.05, 1.00, antenna_largest_dimension_m, 0.01)

            edit_antennas_in_app = st.checkbox(
                "Ajustar posição/ângulo das antenas pelo app",
                value=False,
                help="Use apenas para ensaio. Para apresentação, prefira a geometria do Blender/JSON."
            )
            if edit_antennas_in_app:
                lateral_z = st.slider("Altura das antenas laterais atuais Z (m)", 0.35, 1.80, lateral_z, 0.05)
                lateral_y = st.slider("Deslocamento Y das antenas laterais (m)", -0.45, 0.45, lateral_y, 0.01)
                lateral_tilt_deg = st.slider("Inclinação vertical das laterais (°; negativo aponta para baixo)", -55.0, 55.0, lateral_tilt_deg, 1.0)
                lateral_yaw_deg = st.slider("Yaw das laterais frente/fundo (°; + aponta para o fundo)", -45.0, 45.0, lateral_yaw_deg, 1.0)
                top_z = st.slider("Altura da antena superior Z (m)", 1.60, 2.30, top_z, 0.01)
                top_tilt_x_deg = st.slider("Inclinação da superior em X (°)", -45.0, 45.0, top_tilt_x_deg, 1.0)
                top_tilt_y_deg = st.slider("Inclinação da superior em Y (°; + para o fundo)", -45.0, 45.0, top_tilt_y_deg, 1.0)
                add_lower_side_antennas = st.checkbox("Adicionar par de antenas laterais baixas", value=add_lower_side_antennas)
                if add_lower_side_antennas:
                    lower_lateral_z = st.slider("Altura das laterais baixas Z (m)", 0.35, 1.20, lower_lateral_z, 0.05)
                    lower_lateral_tilt_deg = st.slider("Inclinação das laterais baixas (°; negativo aponta para baixo)", -55.0, 35.0, lower_lateral_tilt_deg, 1.0)

        with st.expander("🏷️ Tags, pilha e volume do enxoval", expanded=False):
            tag_seed = st.number_input("Semente aleatória das tags", 0, 999999, tag_seed, 1)
            tag_distribution = st.selectbox("Distribuição das tags", ["Aleatória uniforme", "Centro mais denso", "Camadas verticais"], index=["Aleatória uniforme", "Centro mais denso", "Camadas verticais"].index(tag_distribution))
            center_concentration = st.slider("Concentração no centro da pilha", 0.0, 1.0, center_concentration, 0.05)
            stack_center_x = st.slider("Centro da pilha X (m)", -0.40, 0.40, stack_center_x, 0.01)
            stack_center_y = st.slider("Centro da pilha Y (m)", -0.40, 0.40, stack_center_y, 0.01)
            stack_center_z = st.slider("Centro da pilha Z (m)", 0.35, 1.40, stack_center_z, 0.01)
            stack_size_x = st.slider("Largura da pilha X (m)", 0.10, 0.75, stack_size_x, 0.01)
            stack_size_y = st.slider("Profundidade da pilha Y (m)", 0.10, 0.85, stack_size_y, 0.01)
            stack_size_z = st.slider("Altura da pilha Z (m)", 0.20, 1.60, stack_size_z, 0.02)

        with st.expander("🧱 Materiais, gaiola e perdas calibráveis", expanded=False):
            override_wall_loss_db = st.slider("Perda por atravessar parede selecionada (dB)", 0.0, 100.0, override_wall_loss_db, 1.0)
            use_cage_loss = st.checkbox("Aplicar perda equivalente da gaiola metálica", value=use_cage_loss)
            cage_extra_diffraction_loss_db = st.slider("Perda extra da grade/difração (dB por cruzamento)", 0.0, 10.0, cage_extra_diffraction_loss_db, 0.5)
            use_textile_loss = st.checkbox("Aplicar atenuação por enxoval/sacos", value=use_textile_loss)
            textile_mode_adv = st.radio("Condição do enxoval avançada", ["Seco", "Úmido", "Manual"], index=0 if textile_mode == "Seco" else 1, horizontal=True)
            if textile_mode_adv == "Seco":
                textile_att_default_adv = float(preset.get("textile_dry_db_per_m", textile.get("attenuation_db_per_m_dry", 12.0)))
            elif textile_mode_adv == "Úmido":
                textile_att_default_adv = float(preset.get("textile_wet_db_per_m", textile.get("attenuation_db_per_m_wet", 25.0)))
            else:
                textile_att_default_adv = textile_attenuation_db_per_m
            textile_attenuation_db_per_m = st.slider("Atenuação do enxoval (dB/m)", 0.0, 80.0, textile_att_default_adv, 1.0)
            use_scale_multipath = st.checkbox("Aplicar penalidade de multipercurso da balança metálica", value=use_scale_multipath)
            scale_multipath_penalty_db = st.slider("Penalidade máx. próxima à balança (dB)", 0.0, 12.0, scale_multipath_penalty_db, 0.5)

        with st.expander("🧲 Inox: multipercurso, robustez e VSWR", expanded=False):
            use_inox_multipath = st.checkbox("Verificar multipercurso de primeira ordem no Inox", value=use_inox_multipath)
            apply_inox_multipath_to_link = st.checkbox("Aplicar correção aproximada de multipercurso no cálculo principal", value=apply_inox_multipath_to_link)
            inox_reflection_coeff_mag = st.slider("Coeficiente de reflexão |Γ| do Inox (aprox.)", 0.0, 1.0, inox_reflection_coeff_mag, 0.05)
            inox_reflection_phase_deg = st.slider("Fase da reflexão aproximada (graus)", 0.0, 360.0, inox_reflection_phase_deg, 15.0)
            inox_multipath_max_boost_db = st.slider("Limite de pico por multipercurso (+dB)", 0.0, 20.0, inox_multipath_max_boost_db, 1.0)
            inox_multipath_max_null_db = st.slider("Limite de vale/cancelamento por multipercurso (-dB)", 0.0, 40.0, inox_multipath_max_null_db, 1.0)
            robustness_grid_per_axis = st.slider("Teste de robustez: pontos por eixo", 3, 5, robustness_grid_per_axis, 1)

        with st.expander("🗺️ Mapas e visualização", expanded=False):
            z_slice = st.slider("Altura do corte Z (m)", 0.05, 2.05, z_slice, 0.05)
            grid_n = st.slider("Resolução do mapa", 25, 100, grid_n, 5)
            x_extent = st.slider("Extensão X do mapa (±m)", 0.8, 3.0, x_extent, 0.1)
            y_min = st.slider("Y mínimo do mapa (frente)", -3.0, -0.5, y_min, 0.1)
            y_max = st.slider("Y máximo do mapa (fundo)", 0.5, 3.0, y_max, 0.1)
            show_vertical_map = st.checkbox("Mostrar mapa vertical do miolo da pilha", value=show_vertical_map)
            vertical_plane = st.selectbox("Plano vertical", ["X-Z com Y fixo", "Y-Z com X fixo"], index=0 if vertical_plane == "X-Z com Y fixo" else 1)
            vertical_fixed_y = st.slider("Y fixo do corte X-Z (m)", -0.60, 0.60, vertical_fixed_y, 0.01)
            vertical_fixed_x = st.slider("X fixo do corte Y-Z (m)", -0.60, 0.60, vertical_fixed_x, 0.01)
            z_min_map = st.slider("Z mínimo do mapa vertical (m)", 0.0, 1.0, z_min_map, 0.05)
            z_max_map = st.slider("Z máximo do mapa vertical (m)", 1.0, 2.30, z_max_map, 0.05)
            reliable_margin_db = st.slider("Margem para leitura confiável (dB)", 0.0, 15.0, reliable_margin_db, 1.0)

    if reader_tx_power_dbm > 33.0:
        st.warning("A potência conduzida calculada passou de 33 dBm. Revise EIRP, ganho da antena ou perda de cabo.")
    if eirp_limit_dbm > 36.0:
        st.error("EIRP acima de 36 dBm / 4 W. Revise a configuração.")
controls = {
    "frequency_hz": freq_mhz * 1e6,
    "reader_tx_power_dbm": reader_tx_power_dbm,
    "eirp_limit_dbm": eirp_limit_dbm,
    "power_mode_eirp": 1.0 if power_mode == "Limite por EIRP (recomendado)" else 0.0,
    "reader_antenna_gain_dbi": reader_antenna_gain_dbi,
    "cable_loss_db": cable_loss_db,
    "tag_activation_dbm": tag_activation_dbm,
    "reader_sensitivity_dbm": reader_sensitivity_dbm,
    "tag_gain_dbi": tag_gain_dbi,
    "backscatter_link_loss_db": backscatter_link_loss_db,
    "polarization_loss_db": polarization_loss_db,
    "tag_orientation_extra_loss_db": tag_orientation_extra_loss_db,
    "antenna_hpbw_deg": antenna_hpbw_deg,
    "antenna_front_to_back_db": antenna_front_to_back_db,
    "antenna_largest_dimension_m": antenna_largest_dimension_m,
    "override_wall_loss_db": override_wall_loss_db,
    "use_cage_loss": 1.0 if use_cage_loss else 0.0,
    "cage_extra_diffraction_loss_db": cage_extra_diffraction_loss_db,
    "use_textile_loss": 1.0 if use_textile_loss else 0.0,
    "textile_attenuation_db_per_m": textile_attenuation_db_per_m,
    "use_scale_multipath": 1.0 if use_scale_multipath else 0.0,
    "scale_multipath_penalty_db": scale_multipath_penalty_db,
    "use_inox_multipath": 1.0 if use_inox_multipath else 0.0,
    "apply_inox_multipath_to_link": 1.0 if apply_inox_multipath_to_link else 0.0,
    "inox_reflection_coeff_mag": inox_reflection_coeff_mag,
    "inox_reflection_phase_deg": inox_reflection_phase_deg,
    "inox_multipath_max_boost_db": inox_multipath_max_boost_db,
    "inox_multipath_max_null_db": inox_multipath_max_null_db,
    "robustness_jitter_radius_m": robustness_jitter_radius_cm / 100.0,
    "robustness_grid_per_axis": float(robustness_grid_per_axis),
}

# Atualiza materiais de painéis conforme seleção global da interface.
for p in scene.get("cabin", {}).get("panels", []):
    p["material"] = selected_wall_material

# Atualiza volume físico do enxoval conforme os controles do app.
scene.setdefault("textile_volume", {})["center"] = [float(stack_center_x), float(stack_center_y), float(stack_center_z)]
scene.setdefault("textile_volume", {})["size"] = [float(stack_size_x), float(stack_size_y), float(stack_size_z)]

# Ajusta antenas no app sem depender de novo JSON do Blender.
if edit_antennas_in_app:
    cabin = scene.get("cabin", {})
    cab_size = cabin.get("size", [1.22, 1.18, 2.10])
    wall_t = float(cabin.get("wall_thickness_m", 0.06))
    x_left = -float(cab_size[0]) / 2.0 + wall_t + 0.025
    x_right = float(cab_size[0]) / 2.0 - wall_t - 0.025

    n_esq = lateral_normal("ESQ", lateral_tilt_deg, lateral_yaw_deg)
    n_dir = lateral_normal("DIR", lateral_tilt_deg, lateral_yaw_deg)
    n_top = top_normal(top_tilt_x_deg, top_tilt_y_deg)

    update_named_antenna(scene, "ESQ", [x_left, lateral_y, lateral_z], n_esq)
    update_named_antenna(scene, "DIR", [x_right, lateral_y, lateral_z], n_dir)
    update_named_antenna(scene, "TOPO", [0.0, float(top0[1]), top_z], n_top)

    # Remove pares baixos antigos se o usuário desligar o recurso.
    scene["antennas"] = [a for a in scene.get("antennas", []) if a.get("name") not in ("ESQ_BAIXA", "DIR_BAIXA")]
    if add_lower_side_antennas:
        n_esq_b = lateral_normal("ESQ", lower_lateral_tilt_deg, lateral_yaw_deg)
        n_dir_b = lateral_normal("DIR", lower_lateral_tilt_deg, lateral_yaw_deg)
        scene["antennas"].append({"name": "ESQ_BAIXA", "position": [x_left, lateral_y, lower_lateral_z], "normal": n_esq_b, "gain_dbi": reader_antenna_gain_dbi, "hpbw_deg": antenna_hpbw_deg, "polarization": "LHCP"})
        scene["antennas"].append({"name": "DIR_BAIXA", "position": [x_right, lateral_y, lower_lateral_z], "normal": n_dir_b, "gain_dbi": reader_antenna_gain_dbi, "hpbw_deg": antenna_hpbw_deg, "polarization": "LHCP"})

# Aplica ganho/abertura global a todas as antenas ativas.
for a in scene.get("antennas", []):
    a["gain_dbi"] = reader_antenna_gain_dbi
    a["hpbw_deg"] = antenna_hpbw_deg

# Gera tags empilhadas dentro do volume de enxoval, preservando probes externos.
if use_generated_stack_tags:
    external_tags = [t for t in scene.get("tags", []) if not bool(t.get("inside_expected", True))]
    stack_tags = generate_stack_tags(
        n_random=n_stack_tags,
        n_buried_center=n_buried_center_tags,
        center=[stack_center_x, stack_center_y, stack_center_z],
        size=[stack_size_x, stack_size_y, stack_size_z],
        seed=int(tag_seed),
        distribution=tag_distribution,
        center_concentration=center_concentration,
    )
    scene["tags"] = stack_tags + external_tags

# Métricas principais
lam = wavelength(controls["frequency_hz"])
d_far = fraunhofer_distance(controls["frequency_hz"], controls["antenna_largest_dimension_m"])
eirp_dbm = reader_tx_power_dbm - cable_loss_db + reader_antenna_gain_dbi

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Comprimento de onda", f"{lam:.3f} m")
c2.metric("Campo distante aprox.", f"{d_far:.2f} m")
c3.metric("P leitor", f"{reader_tx_power_dbm:.1f} dBm")
c4.metric("EIRP", f"{eirp_dbm:.1f} dBm", f"{dbm_to_watts(eirp_dbm):.2f} W")
c5.metric("Material cabine", selected_wall_material)

if d_far > 0.25:
    st.warning(
        "Friis é aproximação de campo distante. Pontos muito próximos da antena ficam sinalizados como campo próximo; "
        "para máxima fidelidade nessa região, seria necessário solver EM full-wave."
    )

with st.expander("📐 Modelo físico usado no cálculo"):
    st.markdown(
        f"""
        **Potência irradiada:**  
        `EIRP = P_leitor - L_cabo + G_antena = {reader_tx_power_dbm:.1f} - {cable_loss_db:.1f} + {reader_antenna_gain_dbi:.1f} = {eirp_dbm:.1f} dBm`

        **Forward link — leitor → tag:** a tag liga se `P_tag ≥ {tag_activation_dbm:.1f} dBm`.

        **Reverse link — tag → leitor:** o leitor detecta se `P_rx ≥ {reader_sensitivity_dbm:.1f} dBm`.  
        Aqui `P_rx dBm` é o **RSSI reverso estimado**.

        **Perdas separadas:** espaço livre, padrão angular da antena, cabo, ganho da tag, polarização circular-linear, orientação/dobra, tecido, gaiola, cabine e backscatter.  
        A perda de backscatter usada aqui é somente a perda adicional de modulação/retroespalhamento; ela não deve incluir novamente FSPL, tecido ou polarização.
        """
    )

# Avaliação das etiquetas

st.subheader("🏷️ Leitura das tags e probes")
rows = []
near_count = 0
for tag in scene.get("tags", []):
    p = arr(tag["position"])
    r = compute_best_link(p, scene, controls)
    near_count += int(bool(r["near_field"]))
    expected_inside = bool(tag.get("inside_expected", True))
    status = classify_margin(r["link_margin_db"], reliable_margin_db)
    if not expected_inside and r["read_ok"]:
        status = "VAZAMENTO / LEITURA INDEVIDA"
    rows.append({
        "Tag/Probe": tag.get("name", "TAG"),
        "Esperada interna?": "Sim" if expected_inside else "Não",
        "Melhor antena": r["antenna"],
        "Distância (m)": round(r["distance_m"], 3),
        "Ângulo (°)": round(r["angle_deg"], 1),
        "P_tag dBm": round(r["p_tag_dbm"], 1),
        "Margem ida dB": round(r["forward_margin_db"], 1),
        "RSSI reverso estimado P_rx dBm": round(r["p_rx_dbm"], 1),
        "Margem volta dB": round(r["reverse_margin_db"], 1),
        "Margem final dB": round(r["link_margin_db"], 1),
        "Perda tecido dB": round(r["textile_loss_db"], 1),
        "Perda gaiola dB": round(r["cage_loss_db"], 1),
        "Perda cabine dB": round(r["cabin_loss_db"], 1),
        "Campo próximo?": "Sim" if r["near_field"] else "Não",
        "Status": status,
    })

df_tags = pd.DataFrame(rows)
st.dataframe(df_tags, use_container_width=True, height=300)

if near_count:
    st.caption(f"{near_count} ponto(s) caíram na região de campo próximo aproximada. O resultado é útil para triagem, mas deve ser calibrado em protótipo.")

# Métricas de tags internas e vazamento
internal = df_tags[df_tags["Esperada interna?"] == "Sim"]
external = df_tags[df_tags["Esperada interna?"] == "Não"]
read_internal = internal[internal["Margem final dB"] >= 0.0]
leak_external = external[external["Margem final dB"] >= 0.0]

m1, m2, m3 = st.columns(3)
m1.metric("Tags internas lidas", f"{len(read_internal)}/{len(internal)}")
m2.metric("Probes externos lidos", f"{len(leak_external)}/{len(external)}", delta="risco" if len(leak_external) else "ok", delta_color="inverse")
m3.metric("Pior margem interna", f"{internal['Margem final dB'].min():.1f} dB" if len(internal) else "-")

if len(internal):
    c_low, c_mid, c_high = st.columns(3)
    low_internal = internal[internal["Tag/Probe"].str.contains("SOTERRADA|PILHA", regex=True, na=False)]
    c_low.metric("Total de tags internas avaliadas", f"{len(internal)}")
    c_mid.metric("Tags geradas/centrais", f"{len(low_internal)}")
    c_high.metric("Margem média interna", f"{internal['Margem final dB'].mean():.1f} dB")

# Mapa de calor

st.subheader("🗺️ Raio X em corte horizontal")
with st.spinner("Calculando mapa de margem de leitura..."):
    xs = np.linspace(-x_extent, x_extent, grid_n)
    ys = np.linspace(y_min, y_max, grid_n)
    margin_grid = np.zeros((len(ys), len(xs)), dtype=float)
    fwd_grid = np.zeros_like(margin_grid)
    rev_grid = np.zeros_like(margin_grid)
    ant_grid: List[List[str]] = []
    for iy, y in enumerate(ys):
        row_ant = []
        for ix, x in enumerate(xs):
            p = np.array([x, y, z_slice], dtype=float)
            r = compute_best_link(p, scene, controls)
            margin_grid[iy, ix] = r["link_margin_db"]
            fwd_grid[iy, ix] = r["forward_margin_db"]
            rev_grid[iy, ix] = r["reverse_margin_db"]
            row_ant.append(r["antenna"])
        ant_grid.append(row_ant)

heat = go.Figure()
heat.add_trace(go.Heatmap(
    x=xs,
    y=ys,
    z=margin_grid,
    zmin=-25,
    zmax=25,
    colorscale=[
        [0.00, "#3b3b3b"],
        [0.25, "#b00020"],
        [0.50, "#f9a825"],
        [0.62, "#fff176"],
        [0.75, "#4caf50"],
        [1.00, "#00e676"],
    ],
    colorbar=dict(title="Margem final (dB)"),
    hovertemplate="X=%{x:.2f} m<br>Y=%{y:.2f} m<br>Margem=%{z:.1f} dB<extra></extra>",
))

# Desenha cabine e gaiola no corte como retângulos.
def add_rect(fig, center, size, name, line_color):
    cx, cy, _ = center
    sx, sy, _ = size
    x0, x1 = cx - sx / 2.0, cx + sx / 2.0
    y0, y1 = cy - sy / 2.0, cy + sy / 2.0
    fig.add_trace(go.Scatter(
        x=[x0, x1, x1, x0, x0],
        y=[y0, y0, y1, y1, y0],
        mode="lines",
        name=name,
        line=dict(color=line_color, width=2),
        hoverinfo="skip",
    ))

cab = scene.get("cabin", {})
if cab:
    add_rect(heat, arr(cab.get("center", [0,0,1.05])), arr(cab.get("size", [1.2,1.2,2.1])), "Cabine", "white")
rz = scene.get("read_zone", {})
if rz:
    add_rect(heat, arr(rz.get("center", [0,0,1.0])), arr(rz.get("size", [1,1,1.8])), "Zona válida", "cyan")
cage = scene.get("cage", {})
if cage:
    add_rect(heat, arr(cage.get("center", [0,0,0.9])), arr(cage.get("size", [0.67,0.80,1.6])), "Gaiola", "orange")

# Antenas no mapa
for ant in scene.get("antennas", []):
    p = arr(ant["position"])
    if abs(p[2] - z_slice) < 0.35 or ant.get("name") == "TOPO":
        heat.add_trace(go.Scatter(x=[p[0]], y=[p[1]], mode="markers+text", text=[ant.get("name", "ANT")], textposition="top center", marker=dict(size=10, symbol="square", color="blue"), name=f"Antena {ant.get('name','')}", hoverinfo="text"))

heat.update_layout(
    title=f"Margem de leitura no corte Z={z_slice:.2f} m — verde lê, vermelho/sombrio falha, amarelo marginal",
    xaxis_title="X (m)",
    yaxis_title="Y (m)",
    height=650,
    yaxis=dict(scaleanchor="x", scaleratio=1),
    margin=dict(l=10, r=10, t=60, b=10),
)
st.plotly_chart(heat, use_container_width=True)

# Corte vertical do miolo da pilha: útil para encontrar tags soterradas no centro.
if show_vertical_map:
    st.subheader("🧬 Corte vertical do miolo — tags soterradas")
    with st.spinner("Calculando mapa vertical de margem..."):
        z_vals = np.linspace(z_min_map, z_max_map, grid_n)
        if vertical_plane == "X-Z com Y fixo":
            h_vals = np.linspace(-x_extent, x_extent, grid_n)
            vgrid = np.zeros((len(z_vals), len(h_vals)), dtype=float)
            for iz, z in enumerate(z_vals):
                for ih, x in enumerate(h_vals):
                    p = np.array([x, vertical_fixed_y, z], dtype=float)
                    vgrid[iz, ih] = compute_best_link(p, scene, controls)["link_margin_db"]
            x_title = "X (m)"
            title = f"Corte X-Z em Y={vertical_fixed_y:.2f} m"
        else:
            h_vals = np.linspace(y_min, y_max, grid_n)
            vgrid = np.zeros((len(z_vals), len(h_vals)), dtype=float)
            for iz, z in enumerate(z_vals):
                for ih, y in enumerate(h_vals):
                    p = np.array([vertical_fixed_x, y, z], dtype=float)
                    vgrid[iz, ih] = compute_best_link(p, scene, controls)["link_margin_db"]
            x_title = "Y (m)"
            title = f"Corte Y-Z em X={vertical_fixed_x:.2f} m"

    vheat = go.Figure()
    vheat.add_trace(go.Heatmap(
        x=h_vals,
        y=z_vals,
        z=vgrid,
        zmin=-25,
        zmax=25,
        colorscale=[
            [0.00, "#3b3b3b"],
            [0.25, "#b00020"],
            [0.50, "#f9a825"],
            [0.62, "#fff176"],
            [0.75, "#4caf50"],
            [1.00, "#00e676"],
        ],
        colorbar=dict(title="Margem final (dB)"),
        hovertemplate=f"{x_title}=%{{x:.2f}}<br>Z=%{{y:.2f}} m<br>Margem=%{{z:.1f}} dB<extra></extra>",
    ))

    def add_rect_2d(fig, h0, h1, z0, z1, name, color):
        fig.add_trace(go.Scatter(
            x=[h0, h1, h1, h0, h0],
            y=[z0, z0, z1, z1, z0],
            mode="lines",
            name=name,
            line=dict(color=color, width=2),
            hoverinfo="skip",
        ))

    # Desenha seções de cabine, gaiola, volume de tecido e zona válida.
    def box_section(bounds_center, bounds_size, fixed_axis_value, plane_kind, name, color):
        c = arr(bounds_center); s = arr(bounds_size) / 2.0
        if plane_kind == "XZ":
            if c[1] - s[1] <= fixed_axis_value <= c[1] + s[1]:
                add_rect_2d(vheat, c[0]-s[0], c[0]+s[0], c[2]-s[2], c[2]+s[2], name, color)
        else:
            if c[0] - s[0] <= fixed_axis_value <= c[0] + s[0]:
                add_rect_2d(vheat, c[1]-s[1], c[1]+s[1], c[2]-s[2], c[2]+s[2], name, color)

    plane_kind = "XZ" if vertical_plane == "X-Z com Y fixo" else "YZ"
    fixed_val = vertical_fixed_y if plane_kind == "XZ" else vertical_fixed_x
    if cab: box_section(cab.get("center", [0,0,1.05]), cab.get("size", [1.2,1.2,2.1]), fixed_val, plane_kind, "Cabine", "white")
    if rz: box_section(rz.get("center", [0,0,1]), rz.get("size", [1,1,1.8]), fixed_val, plane_kind, "Zona válida", "cyan")
    if cage: box_section(cage.get("center", [0,0,0.9]), cage.get("size", [0.67,0.8,1.6]), fixed_val, plane_kind, "Gaiola", "orange")
    if textile and textile.get("enabled", True): box_section(textile.get("center", [0,0,0.8]), textile.get("size", [0.55,0.62,1.2]), fixed_val, plane_kind, "Volume enxoval", "purple")

    # Tags próximas ao corte vertical
    tol = 0.04
    tag_h, tag_zv, tag_txt, tag_col = [], [], [], []
    for row, tag in zip(rows, scene.get("tags", [])):
        if not bool(tag.get("inside_expected", True)):
            continue
        ptag = arr(tag["position"])
        if plane_kind == "XZ":
            close = abs(ptag[1] - fixed_val) <= tol
            h = ptag[0]
        else:
            close = abs(ptag[0] - fixed_val) <= tol
            h = ptag[1]
        if close:
            tag_h.append(h); tag_zv.append(ptag[2]); tag_txt.append(f"{row['Tag/Probe']}<br>{row['Status']}<br>Margem={row['Margem final dB']} dB")
            tag_col.append("green" if row["Margem final dB"] >= reliable_margin_db else ("yellow" if row["Margem final dB"] >= 0 else "red"))
    if tag_h:
        vheat.add_trace(go.Scatter(
            x=tag_h, y=tag_zv, mode="markers",
            marker=dict(size=7, color=tag_col, line=dict(width=1, color="black")),
            text=tag_txt, hoverinfo="text", name="Tags perto do corte",
        ))

    vheat.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Z (m)",
        height=650,
        yaxis=dict(scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(vheat, use_container_width=True)

# MAPA 3D SIMPLIFICADO DE TAGS, ANTENAS E VOLUMES

st.subheader("📦 Cena física simplificada")
fig3d = go.Figure()

# Tags/probes
if scene.get("tags"):
    tag_x, tag_y, tag_z, tag_color, tag_text = [], [], [], [], []
    for row, tag in zip(rows, scene.get("tags", [])):
        p = arr(tag["position"])
        tag_x.append(p[0]); tag_y.append(p[1]); tag_z.append(p[2])
        if "VAZAMENTO" in row["Status"]:
            tag_color.append("orange")
        elif row["Margem final dB"] >= reliable_margin_db:
            tag_color.append("green")
        elif row["Margem final dB"] >= 0:
            tag_color.append("yellow")
        else:
            tag_color.append("red")
        tag_text.append(f"{row['Tag/Probe']}<br>{row['Status']}<br>Margem={row['Margem final dB']} dB")
    fig3d.add_trace(go.Scatter3d(x=tag_x, y=tag_y, z=tag_z, mode="markers", marker=dict(size=5, color=tag_color), text=tag_text, hoverinfo="text", name="Tags/Probes"))

# Antenas e vetores de apontamento
for ant in scene.get("antennas", []):
    p = arr(ant["position"])
    n = norm_vec(ant["normal"])
    q = p + 0.35 * n
    fig3d.add_trace(go.Scatter3d(x=[p[0]], y=[p[1]], z=[p[2]], mode="markers+text", marker=dict(size=6, symbol="square", color="blue"), text=[ant.get("name", "ANT")], textposition="top center", name=f"Antena {ant.get('name','')}"))
    fig3d.add_trace(go.Scatter3d(x=[p[0], q[0]], y=[p[1], q[1]], z=[p[2], q[2]], mode="lines", line=dict(width=5, color="cyan"), showlegend=False))

# Função para desenhar caixa 3D por arestas
BOX_EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
def add_box3d(fig, center, size, name, color):
    c = arr(center); s = arr(size) / 2.0
    pts = np.array([
        [c[0]-s[0], c[1]-s[1], c[2]-s[2]], [c[0]+s[0], c[1]-s[1], c[2]-s[2]],
        [c[0]+s[0], c[1]+s[1], c[2]-s[2]], [c[0]-s[0], c[1]+s[1], c[2]-s[2]],
        [c[0]-s[0], c[1]-s[1], c[2]+s[2]], [c[0]+s[0], c[1]-s[1], c[2]+s[2]],
        [c[0]+s[0], c[1]+s[1], c[2]+s[2]], [c[0]-s[0], c[1]+s[1], c[2]+s[2]],
    ])
    for k, (i,j) in enumerate(BOX_EDGES):
        fig.add_trace(go.Scatter3d(x=[pts[i,0], pts[j,0]], y=[pts[i,1], pts[j,1]], z=[pts[i,2], pts[j,2]], mode="lines", line=dict(color=color, width=3), name=name if k == 0 else None, showlegend=(k == 0)))

if cab: add_box3d(fig3d, cab.get("center", [0,0,1.05]), cab.get("size", [1.2,1.2,2.1]), "Cabine", "white")
if cage: add_box3d(fig3d, cage.get("center", [0,0,0.9]), cage.get("size", [0.67,0.8,1.6]), "Gaiola", "orange")
if textile and textile.get("enabled", True): add_box3d(fig3d, textile.get("center", [0,0,0.8]), textile.get("size", [0.55,0.62,1.2]), "Volume enxoval", "purple")
if rz: add_box3d(fig3d, rz.get("center", [0,0,1]), rz.get("size", [1,1,1.8]), "Zona válida", "cyan")

fig3d.update_layout(
    scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z", aspectmode="data"),
    height=650,
    margin=dict(l=0, r=0, t=40, b=0),
    title="Modelo físico por camadas usado no cálculo",
)
st.plotly_chart(fig3d, use_container_width=True)

# VERIFICAÇÕES ESPECÍFICAS PARA CABINE METÁLICA / INOX

st.subheader("🧲 Verificação de multipercurso no Inox e risco de VSWR")
st.caption(
    "Esta seção não substitui openEMS nem medição com VNA. Ela adiciona verificações de engenharia: "
    "reflexões de primeira ordem por método das imagens, robustez por deslocamento local e risco geométrico de S11/VSWR."
)

mp_df = multipath_tag_rows(scene, controls, reliable_margin_db)
rob_df = robustness_jitter_rows(scene, controls, reliable_margin_db)
vswr_df = vswr_risk_rows(scene, controls)

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
if not mp_df.empty:
    max_boost = float(mp_df["delta_multipercurso_primeira_ordem_db"].max())
    max_null = float(mp_df["delta_multipercurso_primeira_ordem_db"].min())
    changed = int((mp_df["status_sem"] != mp_df["status_com_aprox"]).sum())
else:
    max_boost = max_null = 0.0; changed = 0
mcol1.metric("Maior pico estimado", f"{max_boost:+.1f} dB")
mcol2.metric("Maior vale estimado", f"{max_null:+.1f} dB")
mcol3.metric("Tags com status alterado", changed)
if not rob_df.empty:
    high_risk = int(rob_df["risco_robustez"].astype(str).str.contains("ALTO").sum())
else:
    high_risk = 0
mcol4.metric("Tags com robustez crítica", high_risk)

with st.expander("📋 Multipercurso aproximado por Inox — método das imagens"):
    st.write(
        "O delta positivo indica possível pico por soma construtiva. Delta negativo indica possível vale/cancelamento. "
        "O cálculo é de primeira ordem e não resolve modos completos de cavidade."
    )
    st.dataframe(mp_df, use_container_width=True, height=350)
    st.download_button(
        "⬇️ Baixar multipercurso Inox (CSV)",
        data=mp_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="05_multipercurso_inox.csv",
        mime="text/csv",
    )

with st.expander("📋 Robustez por deslocamento local das tags"):
    st.write(
        "Para cada tag interna, o app desloca a posição em uma vizinhança local. "
        "Se pequenas mudanças criam falha, a região é sensível a zonas mortas, multipercurso ou geometria de antena."
    )
    st.dataframe(rob_df, use_container_width=True, height=350)
    st.download_button(
        "⬇️ Baixar robustez por posição (CSV)",
        data=rob_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="06_robustez_posicao.csv",
        mime="text/csv",
    )

with st.expander("📋 Risco geométrico de VSWR/S11 por proximidade antena-metal"):
    st.warning(
        "O app NÃO calcula VSWR real. Ele só aponta risco geométrico. "
        "A validação de VSWR/S11 deve ser feita com VNA, medidor de potência refletida ou telemetria do leitor, com a antena instalada na cabine."
    )
    st.dataframe(vswr_df, use_container_width=True, height=300)
    st.download_button(
        "⬇️ Baixar risco VSWR/S11 (CSV)",
        data=vswr_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="07_risco_vswr.csv",
        mime="text/csv",
    )

# DIAGNÓSTICO E EXPORTAÇÃO DOS RESULTADOS

st.subheader("📊 Diagnóstico físico")
colA, colB = st.columns(2)
with colA:
    grid_loss_preview = 0.0
    cage = scene.get("cage", {})
    if cage:
        pitch = cage.get("grid_pitch_m", [0.15, 0.27])
        grid_loss_preview = grid_equivalent_loss_db(float(pitch[0]), float(pitch[1]), float(cage.get("bar_diameter_m", 0.012)), cage_extra_diffraction_loss_db)
    st.write({
        "perda_equivalente_grade_por_cruzamento_db": round(grid_loss_preview, 2),
        "perda_parede_cabine_db": round(override_wall_loss_db, 2),
        "atenuacao_enxoval_db_m": round(textile_attenuation_db_per_m, 2),
        "campo_distante_minimo_m": round(d_far, 3),
    })
with colB:
    st.markdown(
        "**Leitura correta:** tag lida somente se `forward link` e `reverse link` passarem.  "
        "**Vazamento:** ponto externo com margem ≥ 0 dB.  "
        "**Zona morta:** margem final < 0 dB dentro da zona operacional."
    )

st.markdown("### 📦 Central de exportação de dados")
st.caption(
    "Área organizada para reunião, auditoria e bancada. Use o XLSX completo como arquivo principal; "
    "os CSVs individuais servem para importar no Blender ou conferir etapas específicas."
)

tab_xlsx, tab_csv, tab_mapas, tab_blender = st.tabs([
    "Planilha principal",
    "CSVs técnicos",
    "Mapas",
    "Blender"
])

with tab_xlsx:
    st.markdown("**Arquivo recomendado para enviar e analisar depois da reunião.**")
    try:
        diag_xlsx = build_diagnostic_workbook_bytes(scene, controls, reliable_margin_db, scene_source)
        st.download_button(
            "⬇️ Baixar planilha completa de diagnóstico (XLSX)",
            data=diag_xlsx,
            file_name="diagnostico_link_budget_rfid_v7.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"Não foi possível gerar XLSX neste ambiente ({exc}). Baixe o ZIP/CSV na próxima aba.")

with tab_csv:
    csv = df_tags.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Tags/probes — resultado principal (CSV)",
        data=csv,
        file_name="resultado_tags_rfid.csv",
        mime="text/csv",
        use_container_width=True,
    )
    diag_zip = build_diagnostic_csv_zip_bytes(scene, controls, reliable_margin_db, scene_source)
    st.download_button(
        "⬇️ Diagnóstico completo em CSV/ZIP",
        data=diag_zip,
        file_name="diagnostico_link_budget_rfid_v7_csv.zip",
        mime="application/zip",
        use_container_width=True,
    )
    st.caption("O ZIP inclui resumo, diagnóstico por tag, tag × antena, ablação, multipercurso, robustez e risco VSWR/S11.")

with tab_mapas:
    grid_df = pd.DataFrame(margin_grid, index=[f"y={y:.3f}" for y in ys], columns=[f"x={x:.3f}" for x in xs])
    st.download_button(
        "⬇️ Mapa de margem do corte horizontal (CSV)",
        data=grid_df.to_csv().encode("utf-8-sig"),
        file_name="mapa_margem_rfid.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption("Use este arquivo para auditar o mapa de calor mostrado no app.")

with tab_blender:
    st.markdown(
        """
        Para visualizar no Blender exatamente o que o app calculou, exporte os CSVs técnicos e use o script
        `blender_visualizar_diagnostico_rfid_v1.py`.  
        A visualização no Blender mostra as margens e classificações do app; ela não é solver full-wave.
        """
    )
    st.download_button(
        "⬇️ Pacote CSV para visualização/auditoria",
        data=build_diagnostic_csv_zip_bytes(scene, controls, reliable_margin_db, scene_source),
        file_name="diagnostico_para_blender_rfid_v7.zip",
        mime="application/zip",
        use_container_width=True,
    )

st.markdown("---")
st.caption(
    "Modelo analítico calibrável. Para validação final, medir RSSI/taxa de leitura no protótipo e ajustar: perda de tecido, perda da grade, ganho efetivo da tag, perda de orientação e parâmetros de material."
)

# REFERÊNCIAS TÉCNICAS PARA DOCUMENTAÇÃO DO MODELO

with st.expander("📚 Referências técnicas que justificam os parâmetros"):
    st.markdown(
        """
        - **Friis / FSPL:** modelo de propagação em espaço livre para estimar perda de percurso.  
        - **EIRP:** potência irradiada efetiva do conjunto leitor + cabo + antena. `36 dBm = 4 W`.  
        - **RFID passivo UHF:** leitura depende de dois critérios: ativação da tag no forward link e detecção do backscatter no reverse link.  
        - **Polarização circular-linear:** perda típica inicial de 3 dB quando antena circular lê tag aproximadamente linear.  
        - **Backscatter loss:** parâmetro calibrável que representa a perda adicional da modulação/retroespalhamento da tag; deve ser ajustado com RSSI medido em bancada.  
        - **Tecido/enxoval:** atenuação por metro é parâmetro empírico; use valores seco/úmido e calibre com medições reais.
        - **Multipercurso em Inox:** verificação aproximada por método das imagens; não substitui solver full-wave/openEMS.
        - **VSWR/S11:** não é calculado pelo app; apenas risco geométrico. Medir com VNA ou medidor de potência refletida.
        """
    )
