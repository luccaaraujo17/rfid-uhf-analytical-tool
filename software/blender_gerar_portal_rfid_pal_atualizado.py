# -*- coding: utf-8 -*-
"""
GERADOR BLENDER — PORTAL/CABINE RFID HOSPITALAR COM METADADOS FÍSICOS
Versão: 2026-06-10

Este script cria a cena completa para apresentação e também exporta arquivos separados
para o app analítico:

1) rfid_cena_visual_completa.stl
   - Cena visual completa: cabine, balança, rampa, gaiola, sacos, tags, antenas.
   - Uso: apresentação e conferência dimensional.

2) rfid_cabine_rf_paineis.stl
   - Apenas painéis RF da cabine/portal.
   - Uso: inspeção geométrica, não como ray tracing cego.

3) rfid_zona_leitura.stl
   - Volume fechado da zona operacional de leitura.
   - Uso: referência visual/operacional.

4) rfid_scene_metadata.json
   - Arquivo MAIS IMPORTANTE para o app RFID.
   - Descreve antenas, tags, materiais, gaiola, tecido, balança e zona de leitura.
   - O app usa este JSON para simular o conjunto completo por camadas físicas.

Por que JSON além do STL?
------------------------
Porque uma antena não é obstáculo, uma tag não é parede, o enxoval é volume
atenuador e a gaiola é grade equivalente. Se tudo for exportado como uma malha
única, o simulador perde o papel físico de cada objeto.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Iterable, List

import bpy
from mathutils import Vector

# =============================================================================
# CONFIGURAÇÕES GERAIS
# =============================================================================
def resolver_diretorio_saida() -> Path:
    """
    Resolve um diretório seguro para exportar STL/JSON/BLEND.

    Motivo da função:
    no Windows/Blender, quando o script é executado a partir de um arquivo .blend
    ou de um caminho virtual parecido com "TesteInicial.blend\\script.py", usar
    diretamente o diretório de __file__ pode fazer o Python tentar criar uma
    pasta com o mesmo nome de um arquivo .blend já existente, gerando:

        FileExistsError: [WinError 183] Não é possível criar um arquivo já existente

    Por isso, se qualquer parte do caminho terminar com .blend, exportamos em
    uma pasta irmã chamada "<nome_do_blend>_rfid_outputs". Nos demais casos,
    exportamos em uma subpasta "rfid_outputs" ao lado do script.
    """
    if "__file__" in globals():
        raw = Path(os.path.abspath(__file__))
        base = raw.parent
    else:
        base = Path(os.getcwd())

    # Caso especial: algum componente do caminho é um arquivo/pasta com sufixo .blend.
    for p in [base] + list(base.parents):
        if p.suffix.lower() == ".blend":
            out = p.parent / f"{p.stem}_rfid_outputs"
            out.mkdir(parents=True, exist_ok=True)
            return out

    # Se por algum motivo base for um arquivo, usa a pasta acima.
    if base.exists() and base.is_file():
        base = base.parent

    out = base / "rfid_outputs"

    # Se já existir um arquivo com esse nome, usa alternativa segura.
    if out.exists() and not out.is_dir():
        out = base / "rfid_outputs_dir"

    out.mkdir(parents=True, exist_ok=True)
    return out


OUTPUT_DIR = resolver_diretorio_saida()

# Dimensões reais aproximadas em metros
SCALE_W, SCALE_D, SCALE_H = 1.00, 1.00, 0.12
RAMP_L, RAMP_W, RAMP_THICK = 0.95, 1.00, 0.025
CABIN_W, CABIN_D, CABIN_H, WALL_T = 1.22, 1.18, 2.10, 0.06
CAGE_W, CAGE_D, CAGE_H = 0.67, 0.80, 1.60
ROD_R, GRID_R = 0.012, 0.006
WHEEL_R, WHEEL_DEPTH = 0.055, 0.035
ANT_Z = 1.08
ANT_SIZE_SIDE = (0.0335, 0.2591, 0.2591)  # painel lateral PAL90209H: 259,1 x 259,1 x 33,5 mm
ANT_SIZE_TOP = (0.2591, 0.2591, 0.0335)
READ_ZONE_SIZE = (1.00, 1.00, 1.80)
READ_ZONE_CENTER = (0.0, 0.0, 1.05)
TEXTILE_CENTER = (0.0, 0.0, 0.80)
TEXTILE_SIZE = (0.55, 0.62, 1.20)

FPS = 24
WAIT_SECONDS = 5

# =============================================================================
# LIMPEZA E SETUP
# =============================================================================
def clear_scene() -> None:
    if bpy.ops.object.mode_set.poll():
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    for col in list(bpy.data.collections):
        if col.name not in ("Collection", "Scene Collection"):
            bpy.data.collections.remove(col)

clear_scene()
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"

# O usuário relatou preferência por BLENDER_EEVEE. Mantemos isso como primeira tentativa
# e caímos para EEVEE_NEXT em instalações que exigem o identificador novo.
try:
    scene.render.engine = "BLENDER_EEVEE"
except Exception:
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        pass

try:
    scene.eevee.use_volumetric = True
    scene.eevee.use_volumetric_shadows = True
    scene.eevee.volumetric_tile_size = "2"
    scene.eevee.volumetric_shadow_samples = 64
    scene.eevee.shadow_cube_size = "4096"
    scene.eevee.shadow_cascade_size = "4096"
except Exception:
    pass

# World volumétrico para visualizar feixes das antenas
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
tree = world.node_tree
tree.nodes.clear()
bg = tree.nodes.new(type="ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.005, 0.005, 0.005, 1)
out = tree.nodes.new(type="ShaderNodeOutputWorld")
vol = tree.nodes.new(type="ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = 0.05
vol.inputs["Anisotropy"].default_value = 0.2
tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
tree.links.new(vol.outputs["Volume"], out.inputs["Volume"])

# =============================================================================
# COLEÇÕES E MATERIAIS
# =============================================================================
def new_collection(name: str):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

COL_VIS = new_collection("00_Cena_Visual_Completa")
COL_CABIN_RF = new_collection("01_Cabine_RF_Paineis")
COL_READ_ZONE = new_collection("02_Zona_Leitura")
COL_CAGE = new_collection("03_Gaiola_Visual")
COL_ANT = new_collection("04_Antenas")
COL_TAGS = new_collection("05_Tags_Probes")
COL_HELP = new_collection("06_Cameras_Luzes")


def make_mat(name, color, roughness=0.45, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = color
    mat.blend_method = "BLEND" if alpha < 1 else "OPAQUE"
    mat.use_screen_refraction = alpha < 1
    return mat

MAT_FLOOR = make_mat("Piso cinza", (0.1, 0.1, 0.1, 1), 0.9)
MAT_SCALE = make_mat("Balança metálica", (0.4, 0.4, 0.4, 1), 0.2, 0.8)
MAT_RAMP = make_mat("Rampa metálica", (0.3, 0.3, 0.3, 1), 0.3, 0.8)
MAT_CABIN = make_mat("Painel RF absorvedor", (0.05, 0.05, 0.05, 1), 0.9, 0.0)
MAT_METAL = make_mat("Metal inox", (0.75, 0.75, 0.75, 1), 0.08, 1.0)
MAT_DARK = make_mat("Rodas escuras", (0.02, 0.02, 0.02, 1), 0.8)
MAT_BAG = make_mat("Volume/enxoval atenuador", (0.55, 0.65, 0.85, 0.55), 0.7, 0.0, 0.55)
MAT_TAG = make_mat("Tag RFID", (1.0, 0.78, 0.05, 1), 0.4, 0.0)
MAT_ANT = make_mat("Antena Laird", (0.01, 0.01, 0.01, 1), 0.5, 0.0)
MAT_ZONE = make_mat("Zona válida transparente", (0.0, 0.8, 1.0, 0.18), 0.3, 0.0, 0.18)

# =============================================================================
# FUNÇÕES DE OBJETOS
# =============================================================================
def link_to_collection(obj, collection, also_visual=True):
    # Remove de coleções atuais e adiciona na coleção principal desejada.
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    # Objetos também são ligados à coleção visual quando fizer sentido.
    if also_visual and collection != COL_VIS:
        try:
            COL_VIS.objects.link(obj)
        except RuntimeError:
            pass


def cube_obj(name, loc, scale, mat=None, collection=None, also_visual=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if collection:
        link_to_collection(obj, collection, also_visual=also_visual)
    return obj


def cyl_between(name, p1, p2, radius, mat=None, collection=None, vertices=24, also_visual=True):
    p1, p2 = Vector(p1), Vector(p2)
    mid = (p1 + p2) / 2.0
    direction = p2 - p1
    length = direction.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    if mat:
        obj.data.materials.append(mat)
    if collection:
        link_to_collection(obj, collection, also_visual=also_visual)
    return obj


def set_role(obj, role: str, material_physics: str = ""):
    obj["rf_role"] = role
    if material_physics:
        obj["rf_material"] = material_physics
    return obj

# =============================================================================
# CONSTRUÇÃO DA CENA VISUAL
# =============================================================================
# Piso, balança e rampa
floor = set_role(cube_obj("Piso_visual", (0, -0.35, -0.012), (2.20, 3.20, 0.024), MAT_FLOOR, COL_VIS, also_visual=False), "reflector_visual", "concrete")
scale_obj = set_role(cube_obj("BALANCA_metalica", (0, 0.0, SCALE_H / 2), (SCALE_W, SCALE_D, SCALE_H), MAT_SCALE, COL_VIS, also_visual=False), "reflector", "metal")

ramp_end_y = -SCALE_D / 2
ramp_start_y = ramp_end_y - RAMP_L
ramp_center_y = (ramp_start_y + ramp_end_y) / 2.0
ramp = set_role(cube_obj("RAMPA_metalica", (0, ramp_center_y, SCALE_H / 2), (RAMP_W, RAMP_L, RAMP_THICK), MAT_RAMP, COL_VIS, also_visual=False), "reflector", "metal")
ramp.rotation_euler[0] = math.atan2(SCALE_H, RAMP_L)

# Cabine: painéis físicos RF separados em coleção própria
cab_z = CABIN_H / 2.0
front_y = -CABIN_D / 2.0
left_x = -CABIN_W / 2.0 + WALL_T / 2.0
right_x = CABIN_W / 2.0 - WALL_T / 2.0
back_y = CABIN_D / 2.0 - WALL_T / 2.0
top_z = CABIN_H - WALL_T / 2.0

cabin_objects = []
cabin_objects.append(set_role(cube_obj("RF_Cabine_parede_esq", (-CABIN_W/2 + WALL_T/2, 0, cab_z), (WALL_T, CABIN_D, CABIN_H), MAT_CABIN, COL_CABIN_RF), "rf_barrier", "absorber"))
cabin_objects.append(set_role(cube_obj("RF_Cabine_parede_dir", ( CABIN_W/2 - WALL_T/2, 0, cab_z), (WALL_T, CABIN_D, CABIN_H), MAT_CABIN, COL_CABIN_RF), "rf_barrier", "absorber"))
cabin_objects.append(set_role(cube_obj("RF_Cabine_fundo", (0, CABIN_D/2 - WALL_T/2, cab_z), (CABIN_W, WALL_T, CABIN_H), MAT_CABIN, COL_CABIN_RF), "rf_barrier", "absorber"))
cabin_objects.append(set_role(cube_obj("RF_Cabine_teto", (0, 0, CABIN_H - WALL_T/2), (CABIN_W, CABIN_D, WALL_T), MAT_CABIN, COL_CABIN_RF), "rf_barrier", "absorber"))

# Aro frontal metálico: visual e possível refletor, mas NÃO entra como parede fechada no JSON.
set_role(cube_obj("Aro_frontal_superior_metal", (0, front_y, CABIN_H - WALL_T/2), (CABIN_W, WALL_T, WALL_T), MAT_METAL, COL_VIS, also_visual=False), "reflector", "metal")
set_role(cube_obj("Aro_frontal_esq_metal", (-CABIN_W/2 + WALL_T/2, front_y, CABIN_H/2), (WALL_T, WALL_T, CABIN_H), MAT_METAL, COL_VIS, also_visual=False), "reflector", "metal")
set_role(cube_obj("Aro_frontal_dir_metal", ( CABIN_W/2 - WALL_T/2, front_y, CABIN_H/2), (WALL_T, WALL_T, CABIN_H), MAT_METAL, COL_VIS, also_visual=False), "reflector", "metal")

# Zona de leitura como volume transparente fechado
read_zone = set_role(cube_obj("RF_Zona_Leitura_Operacional", READ_ZONE_CENTER, READ_ZONE_SIZE, MAT_ZONE, COL_READ_ZONE), "read_zone", "none")
read_zone.display_type = "WIRE"

# Gaiola visual completa — o app usa sua perda equivalente via JSON, não as faces do STL.
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
cage_ctrl = bpy.context.object
cage_ctrl.name = "CTRL_GAIOLA_ANIMACAO"
link_to_collection(cage_ctrl, COL_CAGE)
set_role(cage_ctrl, "cage_controller", "metal_grid")

cx, cy = 0.0, 0.0
x1, x2 = cx - CAGE_W / 2.0, cx + CAGE_W / 2.0
y1, y2 = cy - CAGE_D / 2.0, cy + CAGE_D / 2.0
z_bottom = WHEEL_R * 2.0
z_top = z_bottom + CAGE_H
cage_objs = []

corners_bottom = [(x1, y1, z_bottom), (x2, y1, z_bottom), (x2, y2, z_bottom), (x1, y2, z_bottom)]
corners_top = [(x1, y1, z_top), (x2, y1, z_top), (x2, y2, z_top), (x1, y2, z_top)]

for i in range(4):
    cage_objs.append(set_role(cyl_between(f"GAIOLA_coluna_{i+1}", corners_bottom[i], corners_top[i], ROD_R, MAT_METAL, COL_CAGE), "cage_bar", "metal"))
for i in range(4):
    j = (i + 1) % 4
    cage_objs.append(set_role(cyl_between(f"GAIOLA_base_tubo_{i+1}", corners_bottom[i], corners_bottom[j], ROD_R, MAT_METAL, COL_CAGE), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_topo_tubo_{i+1}", corners_top[i], corners_top[j], ROD_R, MAT_METAL, COL_CAGE), "cage_bar", "metal"))

# Grades horizontais a cada 15 cm
z = z_bottom + 0.15
level = 1
while z < z_top - 0.05:
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_frente_H_{level}", (x1,y1,z), (x2,y1,z), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_fundo_H_{level}", (x1,y2,z), (x2,y2,z), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_esq_H_{level}", (x1,y1,z), (x1,y2,z), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_dir_H_{level}", (x2,y1,z), (x2,y2,z), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    z += 0.15
    level += 1

# Grades verticais: frente/fundo a cada 15 cm; laterais a cada 27 cm
x = x1 + 0.15
idx = 1
while x < x2 - 0.05:
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_frente_V_{idx}", (x,y1,z_bottom), (x,y1,z_top), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_fundo_V_{idx}", (x,y2,z_bottom), (x,y2,z_top), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    x += 0.15
    idx += 1

y = y1 + 0.27
idx = 1
while y < y2 - 0.05:
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_esq_V_{idx}", (x1,y,z_bottom), (x1,y,z_top), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    cage_objs.append(set_role(cyl_between(f"GAIOLA_grade_dir_V_{idx}", (x2,y,z_bottom), (x2,y,z_top), GRID_R, MAT_METAL, COL_CAGE, 12), "cage_bar", "metal"))
    y += 0.27
    idx += 1

cage_objs.append(set_role(cube_obj("GAIOLA_base_interna", (cx, cy, z_bottom + 0.025), (CAGE_W*0.92, CAGE_D*0.92, 0.025), MAT_DARK, COL_CAGE), "cage_base", "metal"))

wheel_positions = [
    (x1 + 0.08, y1 + 0.08, WHEEL_R), (x2 - 0.08, y1 + 0.08, WHEEL_R),
    (x1 + 0.08, y2 - 0.08, WHEEL_R), (x2 - 0.08, y2 - 0.08, WHEEL_R),
]
for i, pos in enumerate(wheel_positions, start=1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=WHEEL_R, depth=WHEEL_DEPTH, location=pos, rotation=(math.radians(90), 0, 0))
    wheel = bpy.context.object
    wheel.name = f"GAIOLA_roda_{i}"
    wheel.data.materials.append(MAT_DARK)
    link_to_collection(wheel, COL_CAGE)
    set_role(wheel, "wheel_visual", "rubber")
    cage_objs.append(wheel)

# Volume/enxoval visual — o app usa AABB de atenuação pelo JSON.
bag_specs = [
    (-0.13, -0.15, z_bottom+0.18, 0.18, 0.19, 0.12),
    ( 0.13, -0.14, z_bottom+0.19, 0.18, 0.18, 0.12),
    (-0.12,  0.13, z_bottom+0.41, 0.19, 0.17, 0.12),
    ( 0.00, -0.03, z_bottom+0.67, 0.24, 0.22, 0.13),
]
for i, (dx, dy, dz, sx, sy, sz) in enumerate(bag_specs, start=1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(cx+dx, cy+dy, dz))
    bag = bpy.context.object
    bag.name = f"Saco_Roupa_{i}"
    bag.scale = (sx, sy, sz)
    bag.data.materials.append(MAT_BAG)
    link_to_collection(bag, COL_CAGE)
    set_role(bag, "textile_visual", "textile")
    cage_objs.append(bag)

# Tags internas e probes externas
TAG_DEFS = [
    ("TAG_01", (-0.22, -0.18, 0.45), True),
    ("TAG_02", ( 0.21, -0.16, 0.65), True),
    ("TAG_03", (-0.10,  0.11, 0.90), True),
    ("TAG_04", ( 0.14,  0.18, 1.15), True),
    ("TAG_05", ( 0.03, -0.05, 1.38), True),
    ("PROBE_LATERAL", (1.45, 0.0, 1.0), False),
    ("PROBE_FRENTE", (0.0, -1.85, 1.0), False),
    ("PROBE_PRATELEIRA", (1.20, 0.55, 1.1), False),
]

tag_objs = []
internal_tag_objs = []
for name, pos, inside in TAG_DEFS:
    obj = cube_obj(name, pos, (0.055, 0.006, 0.035), MAT_TAG, COL_TAGS)
    set_role(obj, "tag" if inside else "probe", "rfid_tag")
    tag_objs.append(obj)
    if inside:
        internal_tag_objs.append(obj)

# A gaiola, os sacos e as tags internas se movem juntos no frame de leitura.
# Probes externas não são parentadas, pois representam prateleiras/peças fora da cabine.
for obj in cage_objs + internal_tag_objs:
    obj.parent = cage_ctrl
    obj.matrix_parent_inverse = cage_ctrl.matrix_world.inverted()

# Antenas
left_ant_x = -CABIN_W / 2.0 + WALL_T + 0.025
right_ant_x = CABIN_W / 2.0 - WALL_T - 0.025
top_ant_z = CABIN_H - WALL_T - 0.025

ant_left = set_role(cube_obj("LAIRD_PAL90209H_ESQ", (left_ant_x, -0.03, ANT_Z), ANT_SIZE_SIDE, MAT_ANT, COL_ANT), "antenna", "source")
ant_right = set_role(cube_obj("LAIRD_PAL90209H_DIR", (right_ant_x, -0.03, ANT_Z), ANT_SIZE_SIDE, MAT_ANT, COL_ANT), "antenna", "source")
ant_top = set_role(cube_obj("LAIRD_PAL90209H_TOPO", (0, -0.03, top_ant_z), ANT_SIZE_TOP, MAT_ANT, COL_ANT), "antenna", "source")

# Feixes visuais via spots

def add_spot_light(name, loc, rot, power, color, angle_deg, col):
    bpy.ops.object.light_add(type="SPOT", location=loc, rotation=rot)
    l = bpy.context.object
    l.name = name
    l.data.energy = power
    l.data.color = color
    l.data.spot_size = math.radians(angle_deg)
    l.data.spot_blend = 0.4
    try:
        l.data.shadow_buffer_clip_start = 0.001
        l.data.shadow_buffer_bias = 0.001
        l.data.use_contact_shadow = True
        l.data.contact_shadow_distance = 0.1
        l.data.contact_shadow_bias = 0.001
        l.data.contact_shadow_thickness = 0.05
    except AttributeError:
        pass
    link_to_collection(l, col)
    return l

add_spot_light("SINAL_ESQ", (left_ant_x + 0.05, -0.03, ANT_Z), (0, math.radians(-90), 0), 4500, (0.0, 1.0, 0.5), 65, COL_ANT)
add_spot_light("SINAL_DIR", (right_ant_x - 0.05, -0.03, ANT_Z), (0, math.radians( 90), 0), 4500, (0.0, 1.0, 0.5), 65, COL_ANT)
add_spot_light("SINAL_TOPO", (0, -0.03, top_ant_z - 0.05), (0, 0, 0), 5500, (0.0, 0.6, 1.0), 65, COL_ANT)

# Animação simples de entrada e retorno da gaiola
scene.frame_start = 1
scene.frame_end = 360
scene.render.fps = FPS
WAIT_FRAMES = FPS * WAIT_SECONDS
FRAME_ON_SCALE = 120
FRAME_OFF_SCALE = FRAME_ON_SCALE + WAIT_FRAMES
# Para animar, deslocamos a gaiola para iniciar fora e entrar na cabine.
# As coordenadas dos objetos estão centradas; o controlador move o conjunto.
keyframes = [
    (1, -2.05, 0.00),
    (45, -1.45, 0.00),
    (90, -0.45, SCALE_H),
    (FRAME_ON_SCALE, 0.00, SCALE_H),
    (FRAME_OFF_SCALE, 0.00, SCALE_H),
    (270, -0.45, SCALE_H),
    (315, -1.45, 0.00),
    (359, -2.05, 0.00),
]
for frame, y_desired, z_desired in keyframes:
    cage_ctrl.location = (0, y_desired, z_desired)
    cage_ctrl.keyframe_insert(data_path="location", frame=frame)
try:
    if cage_ctrl.animation_data and cage_ctrl.animation_data.action:
        for fc in cage_ctrl.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
except Exception:
    pass
# Coloca a gaiola no frame de leitura para exportação visual do momento de escaneamento.
scene.frame_set(FRAME_ON_SCALE)
READING_OFFSET = Vector((0.0, 0.0, SCALE_H))

# Câmera e luz ambiente
bpy.ops.object.light_add(type="AREA", location=(0, -4.0, 4.0), rotation=(math.radians(60), 0, 0))
l_amb = bpy.context.object
l_amb.name = "LUZ_AMBIENTE_SUAVE"
l_amb.data.energy = 40
l_amb.data.size = 5.0
link_to_collection(l_amb, COL_HELP)

bpy.ops.object.camera_add(location=(2.8, -3.2, 2.15), rotation=(math.radians(62), 0, math.radians(41)))
cam = bpy.context.object
cam.name = "Camera_visao_geral"
scene.camera = cam
link_to_collection(cam, COL_HELP)

if bpy.context.screen:
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            if space and space.type == "VIEW_3D":
                space.shading.type = "RENDERED"

# =============================================================================
# EXPORTAÇÕES
# =============================================================================
def select_only(objs: Iterable[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        if obj and obj.type == "MESH":
            obj.select_set(True)
    mesh_objs = [o for o in objs if o and o.type == "MESH"]
    if mesh_objs:
        bpy.context.view_layer.objects.active = mesh_objs[0]


def export_selected_stl(filepath: Path) -> None:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        bpy.ops.wm.stl_export(filepath=str(filepath), export_selected_objects=True, apply_modifiers=True)
    except Exception:
        bpy.ops.export_mesh.stl(filepath=str(filepath), use_selection=True, use_mesh_modifiers=True)

# Atualiza dependências antes de exportar o frame de leitura.
bpy.context.view_layer.update()

visual_objs = [o for o in bpy.data.objects if o.type == "MESH" and any(c.name in {"00_Cena_Visual_Completa", "01_Cabine_RF_Paineis", "02_Zona_Leitura", "03_Gaiola_Visual", "04_Antenas", "05_Tags_Probes"} for c in o.users_collection)]
select_only(visual_objs)
export_selected_stl(OUTPUT_DIR / "rfid_cena_visual_completa.stl")

select_only(cabin_objects)
export_selected_stl(OUTPUT_DIR / "rfid_cabine_rf_paineis.stl")

select_only([read_zone])
export_selected_stl(OUTPUT_DIR / "rfid_zona_leitura.stl")

# =============================================================================
# METADADOS FÍSICOS PARA O APP RFID
# =============================================================================
metadata = {
    "schema": "rfid_hospitalar_physics_scene_v1",
    "units": "m",
    "description": "Cena física por camadas gerada no Blender para simulação analítica RFID UHF hospitalar.",
    "generated_files": {
        "visual_stl": "rfid_cena_visual_completa.stl",
        "cabin_rf_stl": "rfid_cabine_rf_paineis.stl",
        "read_zone_stl": "rfid_zona_leitura.stl",
    },
    "rf": {
        "frequency_hz": 915e6,
        "antenna_manufacturer": "Laird Technologies",
        "antenna_model": "PAL90209H",
        "antenna_polarization": "LHCP",
        "antenna_size_m": [0.2591, 0.2591, 0.0335],
        "antenna_front_to_back_db": 20.0,
        "antenna_max_vswr": 1.3,
        "antenna_axial_ratio_db": 1.0,
        "reader_tx_power_dbm": 30.0,
        "reader_sensitivity_dbm": -70.0,
        "tag_activation_dbm": -18.0,
        "reader_antenna_gain_dbi": 9.0,
        "tag_gain_dbi": -1.0,
        "cable_loss_db": 1.0,
        "backscatter_link_loss_db": 35.0,
        "polarization_loss_db": 3.0,
        "tag_orientation_extra_loss_db": 3.0,
        "antenna_hpbw_deg": 70.0,
        "antenna_front_to_back_db": 20.0,
        "antenna_largest_dimension_m": 0.2591,
        "reliable_margin_db": 6.0,
    },
    "materials": {
        "MDF Cru": {"wall_crossing_loss_db": 4.0, "reflection_risk_db": 1.0, "description": "Dielétrico leve; baixa blindagem."},
        "Espuma Anecoica": {"wall_crossing_loss_db": 25.0, "reflection_risk_db": 0.5, "description": "Absorvedor aproximado; calibrar em bancada."},
        "Aço Inox": {"wall_crossing_loss_db": 80.0, "reflection_risk_db": 8.0, "description": "Metal contínuo: bloqueio alto e multipercurso."},
        "Acrílico/Policarbonato": {"wall_crossing_loss_db": 2.0, "reflection_risk_db": 0.5, "description": "Baixa perda; não confina campo sozinho."}
    },
    "cabin": {
        "center": [0.0, 0.0, CABIN_H / 2.0],
        "size": [CABIN_W, CABIN_D, CABIN_H],
        "wall_thickness_m": WALL_T,
        "front_open": True,
        "front_y": front_y,
        "default_wall_material": "Espuma Anecoica",
        "panels": [
            {"name": "left_wall", "plane": "x", "coord": -CABIN_W/2.0, "span_y": [-CABIN_D/2.0, CABIN_D/2.0], "span_z": [0.0, CABIN_H], "material": "Espuma Anecoica"},
            {"name": "right_wall", "plane": "x", "coord": CABIN_W/2.0, "span_y": [-CABIN_D/2.0, CABIN_D/2.0], "span_z": [0.0, CABIN_H], "material": "Espuma Anecoica"},
            {"name": "back_wall", "plane": "y", "coord": CABIN_D/2.0, "span_x": [-CABIN_W/2.0, CABIN_W/2.0], "span_z": [0.0, CABIN_H], "material": "Espuma Anecoica"},
            {"name": "ceiling", "plane": "z", "coord": CABIN_H, "span_x": [-CABIN_W/2.0, CABIN_W/2.0], "span_y": [-CABIN_D/2.0, CABIN_D/2.0], "material": "Espuma Anecoica"},
        ]
    },
    "read_zone": {
        "center": list(READ_ZONE_CENTER),
        "size": list(READ_ZONE_SIZE),
        "z_min": READ_ZONE_CENTER[2] - READ_ZONE_SIZE[2] / 2.0,
        "z_max": READ_ZONE_CENTER[2] + READ_ZONE_SIZE[2] / 2.0,
    },
    "cage": {
        "center": [0.0, 0.0, z_bottom + CAGE_H / 2.0 + SCALE_H],
        "size": [CAGE_W, CAGE_D, CAGE_H],
        "grid_pitch_m": [0.15, 0.27],
        "bar_diameter_m": GRID_R * 2.0,
        "extra_diffraction_loss_db": 1.5,
        "enabled": True,
        "note": "A gaiola é representada no app por perda equivalente de grade, não por colisão de barras do STL."
    },
    "textile_volume": {
        "center": [TEXTILE_CENTER[0], TEXTILE_CENTER[1], TEXTILE_CENTER[2] + SCALE_H],
        "size": list(TEXTILE_SIZE),
        "attenuation_db_per_m_dry": 18.0,
        "attenuation_db_per_m_wet": 35.0,
        "enabled": True,
        "note": "Volume atenuador aproximado dos sacos/enxoval. Calibrar com medidas reais."
    },
    "scale": {
        "center": [0.0, 0.0, SCALE_H / 2.0],
        "size": [SCALE_W, SCALE_D, SCALE_H],
        "metal_reflection_penalty_db": 2.0,
        "enabled": True,
        "note": "Representa risco de multipercurso/reflexão metálica, não bloqueio direto."
    },
    "antennas": [
        {"name": "ESQ", "position": [left_ant_x, -0.03, ANT_Z], "normal": [1.0, 0.0, 0.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"},
        {"name": "DIR", "position": [right_ant_x, -0.03, ANT_Z], "normal": [-1.0, 0.0, 0.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"},
        {"name": "TOPO", "position": [0.0, -0.03, top_ant_z], "normal": [0.0, 0.0, -1.0], "gain_dbi": 9.0, "hpbw_deg": 70.0, "polarization": "LHCP"}
    ],
    "tags": [
        {
            "name": name,
            "position": [pos[0], pos[1], pos[2] + (SCALE_H if inside else 0.0)],
            "inside_expected": inside
        }
        for name, pos, inside in TAG_DEFS
    ]
}

with open(OUTPUT_DIR / "rfid_scene_metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

# Salva o .blend também, para edição posterior.
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "rfid_portal_hospitalar.blend"))

print("=== ARQUIVOS RFID GERADOS ===")
print(f"Diretório: {OUTPUT_DIR}")
print("- rfid_portal_hospitalar.blend")
print("- rfid_cena_visual_completa.stl")
print("- rfid_cabine_rf_paineis.stl")
print("- rfid_zona_leitura.stl")
print("- rfid_scene_metadata.json")
print("\nUse no app Streamlit: streamlit run app_rfid_raio_x_fisico.py")
