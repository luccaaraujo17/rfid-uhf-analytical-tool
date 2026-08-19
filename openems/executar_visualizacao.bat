@echo off
cd /d "%~dp0"
python 00_verificar_instalacao.py || pause
python 01_visualizar_geometria.py --scenario S2_duas_tags_eps_frontal --mesh media
pause
