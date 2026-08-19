# -*- coding: utf-8 -*-
"""Executa o mesmo cenário nas malhas rápida, média e fina."""
import argparse
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--scenario", default="S2_duas_tags_eps_frontal")
a = p.parse_args()
root = Path(__file__).resolve().parent
for mesh in ["rapida", "media", "fina"]:
    cmd = [sys.executable, str(root / "02_executar_cenario.py"), "--scenario", a.scenario, "--mesh", mesh]
    print("EXECUTANDO", " ".join(cmd))
    subprocess.run(cmd, check=True)
subprocess.run([sys.executable, str(root / "05_consolidar_resultados.py")], check=True)
subprocess.run([sys.executable, str(root / "08_gerar_correcoes_para_app.py")], check=False)
