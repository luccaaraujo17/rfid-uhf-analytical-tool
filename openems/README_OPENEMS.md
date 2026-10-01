# openEMS

Scripts usados como apoio ao estudo de orientação, proximidade entre etiquetas, EPS e material têxtil.

## Ordem básica

```powershell
python 00_verificar_instalacao.py
python 01_visualizar_geometria.py --scenario S0_tag_unica_ar_frontal --mesh rapida
python 02_executar_cenario.py --scenario S0_tag_unica_ar_frontal --mesh rapida
```

Cenários principais:

- `S0_tag_unica_ar_frontal`: referência;
- `S1_tag_unica_eps_frontal`: efeito do EPS;
- `S2_duas_tags_eps_frontal`: duas etiquetas;
- `S3_duas_tags_horizontal`: orientação horizontal;
- `S4_duas_tags_lateral`: orientação lateral;
- `S5_tag_unica_toalha_parametrica`: toalha.

Para executar os cenários básicos:

```powershell
python 04_executar_cenarios_padrao.py --mesh rapida
python 05_consolidar_resultados.py
python 08_gerar_correcoes_para_app.py
```

Os resultados do solver são usados de forma complementar. RSSI do JRFID não deve ser tratado como equivalente direto a campo elétrico, potência na carga ou RCS.
