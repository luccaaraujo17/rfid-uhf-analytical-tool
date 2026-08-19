# openEMS - guia de execução do pacote RFID UHF

## Princípio do modelo

A antena comercial Laird PAL90209H não é reconstruída internamente, pois seus patches, substratos e alimentação não são publicados. O app analítico usa o perfil real de 9 dBic, LHCP, HPBW de 70 graus e relação frente-costas de 20 dB. O openEMS recebe uma onda plana local normalizada de 1 V/m e calcula **correções relativas** de orientação, EPS, proximidade, carga paramétrica e espalhamento.

## Ordem obrigatória

1. Execute `00_verificar_instalacao.py`.
2. Visualize o cenário com `01_visualizar_geometria.py`.
3. Rode primeiro uma malha rápida.
4. Confira os arquivos e os resultados.
5. Repita cenários selecionados em malha média e fina.
6. Gere correções relativas para o app com `08_gerar_correcoes_para_app.py`.

## Comandos principais

```bat
python 01_visualizar_geometria.py --scenario S2_duas_tags_eps_frontal --mesh rapida
python 02_executar_cenario.py --scenario S0_tag_unica_ar_frontal --mesh rapida
python 04_executar_cenarios_padrao.py --mesh rapida
python 05_consolidar_resultados.py
python 08_gerar_correcoes_para_app.py
```

## Cenários

- `S0_tag_unica_ar_frontal`: referência normalizada.
- `S1_tag_unica_eps_frontal`: efeito relativo do EPS.
- `S2_duas_tags_eps_frontal`: duas tags com 55 mm entre centros.
- `S3_duas_tags_horizontal`: rotação horizontal/pitch, 55 mm entre centros.
- `S4_duas_tags_lateral`: rotação lateral/yaw, 55 mm entre centros.
- `S5_tag_unica_toalha_parametrica`: cenário nominal de toalha, ainda paramétrico.

## Varreduras

```bat
python 03_varredura_carga_chip.py --scenario S1_tag_unica_eps_frontal --mesh rapida
python 06_varredura_espacamento_tags.py --mesh rapida
python 07_varredura_toalha_parametrica.py --mesh rapida --limit 3
python 09_estudo_convergencia.py --scenario S2_duas_tags_eps_frontal
```

A varredura completa da toalha contém muitas combinações. Comece com `--limit 3` e só depois amplie.

## Saídas

Cada execução produz uma pasta em `resultados/` contendo:

- `resultado.json`: RCS, tensão, corrente e potência na carga;
- dumps HDF5 `E_fd_915MHz` e `J_fd_915MHz` para inspeção;
- arquivos NF2FF usados no cálculo de RCS;
- estatísticas do solver.

O script `08_gerar_correcoes_para_app.py` calcula, em relação ao S0:

- `delta_load_power_db`;
- `delta_rcs_db`.

Esses deltas podem corrigir o modelo analítico, mas não são convertidos automaticamente em RSSI do leitor.

## Limitações explícitas

- tag e carga são aproximadas e paramétricas;
- toalha não foi caracterizada dieletricamente;
- EPS usa valor inicial próximo do ar;
- a onda no solver é linear; a perda nominal CP-LP é aplicada no app;
- múltiplas antenas virtuais devem ser avaliadas por cobertura individual/melhor margem, salvo quando fases e simultaneidade forem conhecidas;
- o solver Windows incluído não foi executado neste ambiente de criação do pacote.
