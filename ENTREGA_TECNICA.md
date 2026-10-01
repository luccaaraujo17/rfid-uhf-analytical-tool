# Entrega técnica do projeto

Este arquivo resume a organização final do material desenvolvido no projeto.

## Software

- `software/app_rfid_raio_x_fisico_pal_openems_atualizado.py`: aplicação principal;
- `software/rfid_physics_core.py`: núcleo de cálculos;
- `software/app_rfid_validacao_pal_openems.py`: comparação entre modelo, bancada e simulação.

## Medições

Os CSVs originais estão em `bancada/dados/`.

Arquivos de apoio:

- `bancada/RESUMO_RESULTADOS_BANCADA_RFID.xlsx`;
- `bancada/Analise_RFID_UHF_Graficos_Cientificos_Colab_v2.ipynb`;
- `bancada/LEIA_ME_DADOS_BANCADA.txt`.

Foram avaliadas condições de distância, FIELDSTRENGTH, proximidade entre etiquetas, presença de toalha e orientação.

## Modelagem e simulação

- `geometria/`: modelos STL;
- `openems/`: scripts de simulação;
- arquivos de modelagem e metadados usados no estudo.

Os resultados experimentais de bancada são a principal referência quantitativa. O modelo analítico e as simulações foram usados como apoio à interpretação.

## Continuidade

Os relatórios, apresentações e demais documentos também foram organizados na pasta PIC do Google Drive institucional.
