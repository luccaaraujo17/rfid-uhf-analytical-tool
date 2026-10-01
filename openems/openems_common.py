# -*- coding: utf-8 -*-
"""Funções comuns para cenários RFID no openEMS.

O solver local usa onda plana normalizada e uma tag aproximada. A distância e a
potência da antena Laird PAL90209H são tratadas pelo modelo analítico; o openEMS
fornece correções relativas de orientação, EPS, proximidade e espalhamento.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np


def load_config(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_openems_imports():
    try:
        from CSXCAD import ContinuousStructure, AppCSXCAD_BIN
        from openEMS import openEMS
        from openEMS.physical_constants import C0, Z0, EPS0
        from openEMS.ports import UI_data
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível importar CSXCAD/openEMS. Execute 00_verificar_instalacao.py "
            "e confira OPENEMS_INSTALL_PATH/CSXCAD_INSTALL_PATH."
        ) from exc
    return ContinuousStructure, AppCSXCAD_BIN, openEMS, C0, Z0, EPS0, UI_data


def add_box_lines(mesh, axis: str, values):
    vals = sorted(set(float(v) for v in values))
    if vals:
        mesh.AddLine(axis, vals)


def add_meander_tag(
    CSX,
    FDTD,
    center_mm,
    orientation: str,
    tag_cfg: dict,
    name: str,
    chip_r_ohm: float,
    chip_c_pf: float,
    add_load: bool = True,
):
    """Cria inlay aproximado 75 x 20 mm com braços meandriformes e gap central.

    A geometria não identifica uma etiqueta comercial. Ela preserva dimensões,
    polarização linear e uma região de carga paramétrica.
    """
    cx, cy, cz = map(float, center_mm)
    length = float(tag_cfg["size_mm"][1])
    height = float(tag_cfg["size_mm"][2])
    strip = float(tag_cfg["metal_strip_mm"])
    gap = float(tag_cfg["chip_gap_mm"])
    half_l = length / 2.0
    half_h = height / 2.0

    metal = CSX.AddMetal(f"metal_{name}")
    substrate = CSX.AddMaterial(
        f"substrate_{name}",
        epsilon=float(tag_cfg.get("substrate_epsilon_r", 2.5)),
        kappa=float(tag_cfg.get("substrate_kappa_s_m", 0.002)),
    )
    substrate_t = float(tag_cfg.get("substrate_thickness_mm", 0.2))

    def add_segment(a, b):
        metal.AddBox(priority=20, start=a, stop=b)

    # Frontal: plano YZ
    if orientation == "frontal":
        x = cx
        # Braços principais
        add_segment([x, cy-half_l, cz-strip/2], [x, cy-gap/2, cz+strip/2])
        add_segment([x, cy+gap/2, cz-strip/2], [x, cy+half_l, cz+strip/2])
        # Meandros laterais
        for sign in (-1, 1):
            y0 = cy + sign*(gap/2 + 7)
            for i in range(5):
                y = y0 + sign*i*5.0
                z1 = cz-half_h+2 if i % 2 == 0 else cz+2
                z2 = cz-2 if i % 2 == 0 else cz+half_h-2
                add_segment([x, min(y,y+sign*strip), min(z1,z2)], [x, max(y,y+sign*strip), max(z1,z2)])
        substrate.AddBox(
            priority=5,
            start=[x, cy-half_l, cz-half_h],
            stop=[x+substrate_t, cy+half_l, cz+half_h],
        )
        load_start = [x, cy-gap/2, cz-strip/2]
        load_stop = [x, cy+gap/2, cz+strip/2]
        load_dir = "y"
        mesh_edges = {"x":[x], "y":[cy-half_l,cy-gap/2,cy+gap/2,cy+half_l], "z":[cz-half_h,cz,cz+half_h]}

    # Horizontal: plano XY
    elif orientation == "horizontal":
        z = cz
        add_segment([cx-strip/2, cy-half_l, z], [cx+strip/2, cy-gap/2, z])
        add_segment([cx-strip/2, cy+gap/2, z], [cx+strip/2, cy+half_l, z])
        for sign in (-1, 1):
            y0 = cy + sign*(gap/2 + 7)
            for i in range(5):
                y = y0 + sign*i*5.0
                x1 = cx-half_h+2 if i % 2 == 0 else cx+2
                x2 = cx-2 if i % 2 == 0 else cx+half_h-2
                add_segment([min(x1,x2), min(y,y+sign*strip), z], [max(x1,x2), max(y,y+sign*strip), z])
        substrate.AddBox(
            priority=5,
            start=[cx-half_h, cy-half_l, z],
            stop=[cx+half_h, cy+half_l, z+substrate_t],
        )
        load_start = [cx-strip/2, cy-gap/2, z]
        load_stop = [cx+strip/2, cy+gap/2, z]
        load_dir = "y"
        mesh_edges = {"x":[cx-half_h,cx,cx+half_h], "y":[cy-half_l,cy-gap/2,cy+gap/2,cy+half_l], "z":[z]}

    # Lateral: plano XZ
    elif orientation == "lateral":
        y = cy
        add_segment([cx-half_l, y, cz-strip/2], [cx-gap/2, y, cz+strip/2])
        add_segment([cx+gap/2, y, cz-strip/2], [cx+half_l, y, cz+strip/2])
        for sign in (-1, 1):
            x0 = cx + sign*(gap/2 + 7)
            for i in range(5):
                x = x0 + sign*i*5.0
                z1 = cz-half_h+2 if i % 2 == 0 else cz+2
                z2 = cz-2 if i % 2 == 0 else cz+half_h-2
                add_segment([min(x,x+sign*strip), y, min(z1,z2)], [max(x,x+sign*strip), y, max(z1,z2)])
        substrate.AddBox(
            priority=5,
            start=[cx-half_l, y, cz-half_h],
            stop=[cx+half_l, y+substrate_t, cz+half_h],
        )
        load_start = [cx-gap/2, y, cz-strip/2]
        load_stop = [cx+gap/2, y, cz+strip/2]
        load_dir = "x"
        mesh_edges = {"x":[cx-half_l,cx-gap/2,cx+gap/2,cx+half_l], "y":[y], "z":[cz-half_h,cz,cz+half_h]}
    else:
        raise ValueError(f"Orientação desconhecida: {orientation}")

    FDTD.AddEdges2Grid(dirs="xyz", properties=metal, metal_edge_res=1.0)

    if add_load:
        lump = CSX.AddLumpedElement(
            f"chip_{name}",
            ny=load_dir,
            caps=True,
            R=float(chip_r_ohm),
            C=float(chip_c_pf)*1e-12,
        )
        lump.AddBox(priority=30, start=load_start, stop=load_stop)

        u_probe = CSX.AddProbe(f"ut_{name}", p_type=0)
        u_probe.AddBox(priority=40, start=load_start, stop=load_stop)
        i_probe = CSX.AddProbe(f"it_{name}", p_type=1, norm_dir={"x":0,"y":1,"z":2}[load_dir])
        i_probe.AddBox(priority=40, start=load_start, stop=load_stop)

    return mesh_edges


def build_simulation(config: dict, scenario: dict, mesh_preset: str = "media", chip_r=None, chip_c_pf=None):
    ContinuousStructure, AppCSXCAD_BIN, openEMS, C0, Z0, EPS0, UI_data = ensure_openems_imports()

    f0 = float(config["frequency_hz"])
    span = float(config["frequency_span_hz"])
    f_start, f_stop = f0-span/2, f0+span/2
    FDTD = openEMS(NrTS=int(config["max_timesteps"]), EndCriteria=float(config["end_criteria"]))
    FDTD.SetGaussExcite(f0, span/2)
    FDTD.SetBoundaryCond(config["boundary"])

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(1e-3)

    preset = config["mesh_presets"][mesh_preset]
    simbox = np.asarray(config["simulation_box_mm"], dtype=float)
    for axis, extent in zip("xyz", simbox):
        mesh.SetLines(axis, [-extent/2, 0, extent/2])
        mesh.SmoothMeshLines(axis, float(preset["air_mm"]), 1.4)

    eps_cfg = config["eps"]
    eps_size = np.asarray(eps_cfg["size_mm"], dtype=float)
    eps_front_x = -eps_size[0]/2.0
    if scenario.get("eps", False):
        eps = CSX.AddMaterial("EPS", epsilon=float(eps_cfg["epsilon_r"]), kappa=float(eps_cfg["kappa_s_m"]))
        eps.AddBox(priority=1, start=-eps_size/2, stop=eps_size/2)
        add_box_lines(mesh, "x", [-eps_size[0]/2, eps_size[0]/2])
        add_box_lines(mesh, "y", [-eps_size[1]/2, eps_size[1]/2])
        add_box_lines(mesh, "z", [-eps_size[2]/2, eps_size[2]/2])

    towel_cfg = {**config.get("towel", {}), **scenario.get("towel_overrides", {})}
    towel_size = np.asarray(towel_cfg.get("size_mm", [20.0, 250.0, 250.0]), dtype=float)
    if scenario.get("towel", False):
        towel = CSX.AddMaterial(
            "TOALHA_PARAMETRICA",
            epsilon=float(towel_cfg.get("epsilon_r", 1.6)),
            kappa=float(towel_cfg.get("kappa_s_m", 0.02)),
        )
        towel.AddBox(priority=2, start=-towel_size/2, stop=towel_size/2)
        for ax, vals in zip("xyz", [[-towel_size[0]/2,towel_size[0]/2],[-towel_size[1]/2,towel_size[1]/2],[-towel_size[2]/2,towel_size[2]/2]]):
            add_box_lines(mesh, ax, vals)

    tag_cfg = config["tag"]
    r = float(chip_r if chip_r is not None else tag_cfg["chip_r_ohm"])
    c_pf = float(chip_c_pf if chip_c_pf is not None else tag_cfg["chip_c_pf"])

    tag_names=[]
    local_edges={"x":[],"y":[],"z":[]}
    for idx,t in enumerate(scenario["tags"], start=1):
        orient=t.get("orientation","frontal")
        y=float(t.get("offset_y_mm",0.0))
        z=float(t.get("offset_z_mm",0.0))
        if scenario.get("eps",False):
            z=-eps_size[2]/2 + float(t.get("height_mm",eps_size[2]/2))
            # Metal na face incidente
            x=eps_front_x-float(tag_cfg.get("substrate_thickness_mm",0.2))
        elif scenario.get("towel",False):
            # A onda atravessa a toalha antes da etiqueta
            x=towel_size[0]/2.0 + 0.05
            z=float(t.get("offset_z_mm",0.0))
        else:
            x=0.0
            if "height_mm" in t and orient=="frontal": z=float(t["height_mm"])-eps_size[2]/2
        name=f"tag{idx}"
        tag_names.append(name)
        edges=add_meander_tag(CSX,FDTD,[x,y,z],orient,tag_cfg,name,r,c_pf,add_load=True)
        for ax in local_edges: local_edges[ax].extend(edges[ax])

    for ax,vals in local_edges.items():
        add_box_lines(mesh,ax,vals)
    mesh.SmoothMeshLines("all", float(preset["local_mm"]), 1.35)

    # Onda plana linear normalizada
    pw_cfg=config["plane_wave"]
    pw=CSX.AddExcitation("plane_wave",exc_type=10,exc_val=pw_cfg["electric_field_direction"])
    pw.SetPropagationDir(pw_cfg["propagation_direction"])
    pw.SetFrequency(f0)
    pwbox=np.asarray(config["plane_wave_box_mm"],dtype=float)
    pw.AddBox(-pwbox/2,pwbox/2)

    # Resultados em domínio da frequência
    dump_box = np.asarray(config.get("local_dump_box_mm", [180, 260, 260]), dtype=float)
    e_dump = CSX.AddDump("E_fd_915MHz", dump_type=10, file_type=1, frequency=[f0], dump_mode=2)
    e_dump.AddBox(priority=0, start=-dump_box/2, stop=dump_box/2)
    j_dump = CSX.AddDump("J_fd_915MHz", dump_type=12, file_type=1, frequency=[f0], dump_mode=0)
    j_dump.AddBox(priority=0, start=-dump_box/2, stop=dump_box/2)

    nf2ff=FDTD.CreateNF2FFBox()
    return {
        "FDTD":FDTD,"CSX":CSX,"mesh":mesh,"nf2ff":nf2ff,
        "tag_names":tag_names,"f0":f0,"f_start":f_start,"f_stop":f_stop,
        "UI_data":UI_data,"Z0":Z0,"AppCSXCAD_BIN":AppCSXCAD_BIN,
        "scenario":scenario,"chip_r":r,"chip_c_pf":c_pf,
        "electric_field_direction":pw_cfg["electric_field_direction"],
        "towel_parameters":towel_cfg if scenario.get("towel",False) else None,
    }


def postprocess(sim, sim_path: str | Path) -> dict:
    sim_path=str(sim_path)
    f0=sim["f0"]
    UI_data=sim["UI_data"]
    Z0=sim["Z0"]
    E_dir=np.asarray(sim.get("electric_field_direction",[0,1,0]),dtype=float)
    ef=UI_data("et",sim_path,freq=f0)
    pin=0.5*np.linalg.norm(E_dir)**2/Z0*abs(ef.ui_f_val[0])**2
    nf=sim["nf2ff"].CalcNF2FF(sim_path,f0,90,180,outfile="back_nf2ff.h5")
    rcs=float(4*math.pi/pin[0]*nf.P_rad[0][0][0])
    tags=[]
    for name in sim["tag_names"]:
        item={"tag":name}
        try:
            u=UI_data(f"ut_{name}",sim_path,freq=f0)
            i=UI_data(f"it_{name}",sim_path,freq=f0)
            v=complex(np.asarray(u.ui_f_val[0]).reshape(-1)[0])
            current=complex(np.asarray(i.ui_f_val[0]).reshape(-1)[0])
            p=0.5*float(np.real(v*np.conj(current)))
            item.update({"voltage_v_complex":[v.real,v.imag],"current_a_complex":[current.real,current.imag],"load_power_w":p})
        except Exception as exc:
            item["probe_warning"]=str(exc)
        tags.append(item)
    return {
        "scenario":sim["scenario"]["name"],
        "frequency_hz":f0,
        "chip_r_ohm":sim["chip_r"],
        "chip_c_pf":sim["chip_c_pf"],
        "backscatter_rcs_m2":rcs,
        "towel_parameters":sim.get("towel_parameters"),
        "tags":tags,
        "interpretation":"Resultados normalizados para onda linear de 1 V/m. Escalar no app pela intensidade de campo calculada para PAL90209H."
    }
