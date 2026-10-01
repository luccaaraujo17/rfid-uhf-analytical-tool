# Software

Arquivos principais:

- `app_rfid_raio_x_fisico_pal_openems_atualizado.py`: aplicação principal;
- `rfid_physics_core.py`: cálculos do enlace RFID;
- `app_rfid_validacao_pal_openems.py`: comparação entre modelo, bancada e simulação;
- `testar_nucleo_matematico.py`: teste básico do núcleo.

Instalação:

```powershell
pip install -r requirements_app.txt
```

Execução:

```powershell
streamlit run app_rfid_raio_x_fisico_pal_openems_atualizado.py
```

Os parâmetros experimentais devem ser conferidos com os dados da bancada. O openEMS é usado como apoio para estudar efeitos relativos de orientação, material e proximidade entre etiquetas.
