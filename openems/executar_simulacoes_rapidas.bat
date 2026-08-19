@echo off
cd /d "%~dp0"
python 04_executar_cenarios_padrao.py --mesh rapida
if errorlevel 1 goto erro
python 05_consolidar_resultados.py
python 08_gerar_correcoes_para_app.py
if errorlevel 1 echo A referencia S0 pode ainda nao ter sido concluida.
echo.
echo Simulacoes rapidas concluidas. Consulte a pasta resultados.
pause
exit /b 0
:erro
echo Ocorreu uma falha. Leia a mensagem acima e teste primeiro 00_verificar_instalacao.py.
pause
exit /b 1
