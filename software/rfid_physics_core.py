# -*- coding: utf-8 -*-
"""Núcleo físico-matemático do estudo RFID UHF.

Este módulo separa o modelo analítico do aplicativo da calibração experimental e
mantém explícitas as hipóteses usadas no link budget.

Princípios:
- Friis e campo distante são o núcleo analítico;
- a antena real é representada por perfil de ganho/HPBW/FTB;
- a tag desconhecida é um modelo aproximado e paramétrico;
- resultados experimentais não substituem constantes físicas;
- toda comparação esperado x medido deve reportar bias, MAE e RMSE.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Optional, Sequence
import math
import numpy as np

C0 = 299_792_458.0
EPS = 1e-15


def dbm_to_watt(dbm: float) -> float:
    return 10.0 ** ((float(dbm) - 30.0) / 10.0)


def watt_to_dbm(watt: float) -> float:
    return 10.0 * math.log10(max(float(watt), EPS) * 1000.0)


def db_to_linear(db: float) -> float:
    return 10.0 ** (float(db) / 10.0)


def linear_to_db(value: float) -> float:
    return 10.0 * math.log10(max(float(value), EPS))


def wavelength_m(frequency_hz: float) -> float:
    return C0 / float(frequency_hz)


def fraunhofer_distance_m(frequency_hz: float, largest_dimension_m: float) -> float:
    lam = wavelength_m(frequency_hz)
    return 2.0 * float(largest_dimension_m) ** 2 / lam


def fspl_db(distance_m: float, frequency_hz: float) -> float:
    distance_m = max(float(distance_m), 1e-9)
    return 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength_m(frequency_hz))


def mismatch_loss_from_vswr_db(vswr: float) -> float:
    vswr = max(float(vswr), 1.0)
    gamma = (vswr - 1.0) / (vswr + 1.0)
    return -10.0 * math.log10(max(1.0 - gamma * gamma, EPS))


def field_strength_far_v_per_m(tx_power_dbm: float, gain_dbi: float, distance_m: float) -> float:
    """Módulo de E em campo distante: sqrt(30 P G)/R."""
    p_w = dbm_to_watt(tx_power_dbm)
    g_lin = db_to_linear(gain_dbi)
    return math.sqrt(30.0 * p_w * g_lin) / max(float(distance_m), 1e-9)


def angular_gain_dbi(
    peak_gain_dbi: float,
    off_axis_deg: float,
    hpbw_deg: float,
    front_to_back_db: float,
) -> float:
    """Modelo parabólico: A(theta)=min(12(theta/HPBW)^2, A_m)."""
    attenuation = min(
        12.0 * (abs(float(off_axis_deg)) / max(float(hpbw_deg), 1e-9)) ** 2,
        float(front_to_back_db),
    )
    return float(peak_gain_dbi) - attenuation


def normalize(v: Sequence[float]) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    n = np.linalg.norm(a)
    if n < EPS:
        raise ValueError("Vetor de orientação não pode ser nulo.")
    return a / n


def angle_deg(v1: Sequence[float], v2: Sequence[float]) -> float:
    a, b = normalize(v1), normalize(v2)
    return math.degrees(math.acos(float(np.clip(np.dot(a, b), -1.0, 1.0))))


def tag_axis_orientation_loss_db(
    propagation_direction: Sequence[float],
    tag_dipole_axis: Sequence[float],
    max_extra_loss_db: float = 20.0,
) -> float:
    """Perda adicional aproximada da orientação 3D da tag.

    Para uma tag dipolar, apenas a componente do eixo do dipolo transversal à
    direção de propagação participa do acoplamento. A potência relativa é
    aproximada por 1-(u.k)^2. A perda CP-LP nominal de 3 dB deve ser aplicada
    separadamente.
    """
    k = normalize(propagation_direction)
    u = normalize(tag_dipole_axis)
    transverse_power = max(1.0 - float(np.dot(u, k)) ** 2, 10.0 ** (-max_extra_loss_db / 10.0))
    return min(-10.0 * math.log10(transverse_power), float(max_extra_loss_db))


@dataclass(frozen=True)
class AntennaProfile:
    manufacturer: str = "Laird Technologies"
    model: str = "PAL90209H"
    frequency_min_hz: float = 902e6
    frequency_max_hz: float = 928e6
    nominal_frequency_hz: float = 915e6
    peak_gain_dbic: float = 9.0
    hpbw_azimuth_deg: float = 70.0
    front_to_back_db: float = 20.0
    polarization: str = "LHCP"
    axial_ratio_db: float = 1.0
    max_vswr: float = 1.3
    impedance_ohm: float = 50.0
    largest_dimension_m: float = 0.2591
    size_m: tuple[float, float, float] = (0.2591, 0.2591, 0.0335)


@dataclass(frozen=True)
class TagProfile:
    description: str = "Etiqueta UHF passiva adesiva aproximada 75 x 20 mm"
    width_m: float = 0.075
    height_m: float = 0.020
    substrate_thickness_m: float = 0.0002
    nominal_frequency_hz: float = 915e6
    gain_dbi: float = 0.0
    activation_threshold_dbm: float = -18.0
    polarization: str = "linear"
    chip_r_ohm_initial: float = 20.0
    chip_c_pf_initial: float = 1.0
    model_status: str = "aproximado e paramétrico; fabricante/chip não identificados"


@dataclass(frozen=True)
class LinkBudgetInput:
    distance_m: float
    conducted_power_dbm: float
    cable_loss_db: float = 1.0
    antenna_off_axis_deg: float = 0.0
    polarization_loss_db: float = 3.0
    orientation_extra_loss_db: float = 0.0
    material_one_way_loss_db: float = 0.0
    other_one_way_loss_db: float = 0.0
    backscatter_equivalent_loss_db: float = 28.0
    reader_sensitivity_dbm: float = -90.0
    frequency_hz: float = 915e6


@dataclass(frozen=True)
class LinkBudgetResult:
    wavelength_m: float
    fraunhofer_m: float
    in_far_field: bool
    fspl_one_way_db: float
    antenna_gain_effective_dbic: float
    antenna_mismatch_loss_db: float
    eirp_dbm: float
    field_strength_v_per_m: float
    p_tag_dbm: float
    p_rx_dbm: float
    forward_margin_db: float
    reverse_margin_db: float
    final_margin_db: float
    classification: str

    def as_dict(self) -> dict:
        return asdict(self)


def compute_link_budget(
    inp: LinkBudgetInput,
    antenna: AntennaProfile = AntennaProfile(),
    tag: TagProfile = TagProfile(),
    reliable_margin_db: float = 6.0,
) -> LinkBudgetResult:
    freq = float(inp.frequency_hz)
    lam = wavelength_m(freq)
    rff = fraunhofer_distance_m(freq, antenna.largest_dimension_m)
    gain_eff = angular_gain_dbi(
        antenna.peak_gain_dbic,
        inp.antenna_off_axis_deg,
        antenna.hpbw_azimuth_deg,
        antenna.front_to_back_db,
    )
    mismatch = mismatch_loss_from_vswr_db(antenna.max_vswr)
    fspl = fspl_db(inp.distance_m, freq)
    eirp = inp.conducted_power_dbm - inp.cable_loss_db - mismatch + gain_eff
    one_way = (
        fspl
        + inp.polarization_loss_db
        + inp.orientation_extra_loss_db
        + inp.material_one_way_loss_db
        + inp.other_one_way_loss_db
    )
    p_tag = (
        inp.conducted_power_dbm
        - inp.cable_loss_db
        - mismatch
        + gain_eff
        + tag.gain_dbi
        - one_way
    )
    p_rx = (
        inp.conducted_power_dbm
        - 2.0 * inp.cable_loss_db
        - 2.0 * mismatch
        + 2.0 * gain_eff
        + 2.0 * tag.gain_dbi
        - 2.0 * one_way
        - inp.backscatter_equivalent_loss_db
    )
    fm = p_tag - tag.activation_threshold_dbm
    rm = p_rx - inp.reader_sensitivity_dbm
    final = min(fm, rm)
    if final >= reliable_margin_db:
        cls = "LEITURA CONFIÁVEL"
    elif final >= 0.0:
        cls = "LEITURA MARGINAL"
    else:
        cls = "FALHA PREVISTA"
    return LinkBudgetResult(
        wavelength_m=lam,
        fraunhofer_m=rff,
        in_far_field=inp.distance_m >= rff,
        fspl_one_way_db=fspl,
        antenna_gain_effective_dbic=gain_eff,
        antenna_mismatch_loss_db=mismatch,
        eirp_dbm=eirp,
        field_strength_v_per_m=field_strength_far_v_per_m(
            inp.conducted_power_dbm - inp.cable_loss_db - mismatch,
            gain_eff,
            inp.distance_m,
        ),
        p_tag_dbm=p_tag,
        p_rx_dbm=p_rx,
        forward_margin_db=fm,
        reverse_margin_db=rm,
        final_margin_db=final,
        classification=cls,
    )


def comparison_metrics(expected: Iterable[float], measured: Iterable[float]) -> dict:
    expected_a = np.asarray(list(expected), dtype=float)
    measured_a = np.asarray(list(measured), dtype=float)
    if expected_a.shape != measured_a.shape or expected_a.size == 0:
        raise ValueError("Vetores esperado e medido devem ter o mesmo tamanho e não podem ser vazios.")
    error = measured_a - expected_a
    return {
        "n": int(error.size),
        "bias_db": float(np.mean(error)),
        "mae_db": float(np.mean(np.abs(error))),
        "rmse_db": float(np.sqrt(np.mean(error ** 2))),
        "std_error_db": float(np.std(error, ddof=1)) if error.size > 1 else 0.0,
    }


def monte_carlo_link_budget(
    inp: LinkBudgetInput,
    antenna: AntennaProfile = AntennaProfile(),
    tag: TagProfile = TagProfile(),
    n_samples: int = 5000,
    seed: int = 42,
    sigma_cable_db: float = 0.25,
    sigma_gain_db: float = 0.75,
    sigma_orientation_db: float = 1.5,
    sigma_material_db: float = 1.5,
    sigma_backscatter_db: float = 3.0,
) -> dict:
    """Propaga incertezas epistemológicas sem alterar o modelo nominal."""
    rng = np.random.default_rng(seed)
    margins = []
    p_rx = []
    p_tag = []
    for _ in range(int(n_samples)):
        ant_i = AntennaProfile(**{
            **asdict(antenna),
            "peak_gain_dbic": antenna.peak_gain_dbic + rng.normal(0.0, sigma_gain_db),
        })
        inp_i = LinkBudgetInput(**{
            **asdict(inp),
            "cable_loss_db": max(0.0, inp.cable_loss_db + rng.normal(0.0, sigma_cable_db)),
            "orientation_extra_loss_db": max(0.0, inp.orientation_extra_loss_db + rng.normal(0.0, sigma_orientation_db)),
            "material_one_way_loss_db": max(0.0, inp.material_one_way_loss_db + rng.normal(0.0, sigma_material_db)),
            "backscatter_equivalent_loss_db": max(0.0, inp.backscatter_equivalent_loss_db + rng.normal(0.0, sigma_backscatter_db)),
        })
        res = compute_link_budget(inp_i, ant_i, tag)
        margins.append(res.final_margin_db)
        p_rx.append(res.p_rx_dbm)
        p_tag.append(res.p_tag_dbm)
    def q(v):
        a = np.asarray(v)
        return {
            "p05": float(np.quantile(a, 0.05)),
            "p50": float(np.quantile(a, 0.50)),
            "p95": float(np.quantile(a, 0.95)),
            "mean": float(np.mean(a)),
            "std": float(np.std(a, ddof=1)),
        }
    return {
        "samples": int(n_samples),
        "final_margin_db": q(margins),
        "p_rx_dbm": q(p_rx),
        "p_tag_dbm": q(p_tag),
        "probability_margin_positive": float(np.mean(np.asarray(margins) >= 0.0)),
        "probability_margin_reliable": float(np.mean(np.asarray(margins) >= 6.0)),
    }
