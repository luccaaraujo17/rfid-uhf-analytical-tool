# Entrega técnica do projeto

**Projeto:** Estudo de Viabilidade de Implementação de Sistema Inteligente de Identificação e Gestão Automatizada de Enxovais Hospitalares  
**Aluno:** Lucca Nunes dos Santos Pereira de Araújo  
**Curso:** Engenharia Elétrica - UFCG

## Repositório

https://github.com/luccaaraujo17/rfid-uhf-analytical-tool

O repositório reúne o código-fonte, dados de bancada, scripts de análise, geometrias e simulações.

## Software

- `software/app_rfid_raio_x_fisico_pal_openems_atualizado.py`: aplicação principal;
- `software/rfid_physics_core.py`: núcleo de cálculos;
- `software/app_rfid_validacao_pal_openems.py`: comparação entre modelo, bancada e simulação;
- `software/blender_gerar_portal_rfid_pal_atualizado.py`: geração da modelagem 3D.

## Medições de bancada

Os CSVs estão em `bancada/dados/`.

Arquivos principais:

- `bancada/RESUMO_RESULTADOS_BANCADA_RFID.xlsx`;
- `bancada/Analise_RFID_UHF_Graficos_Cientificos_Colab_v2.ipynb`;
- `bancada/LEIA_ME_DADOS_BANCADA.txt`.

Foram avaliadas distância, nível nominal de FIELDSTRENGTH, proximidade entre etiquetas, presença de toalha e orientação.

## Modelagem e simulação

- `geometria/`: modelos STL;
- `openems/`: scripts e configurações de simulação;
- `PARAMETROS_E_HIPOTESES.md`: parâmetros usados e limitações do modelo.

Os resultados experimentais de bancada são a principal referência quantitativa do trabalho. O modelo analítico e as simulações foram usados como apoio à interpretação.

## Documentação

A documentação acadêmica e as cópias organizadas do material estão no Google Drive institucional:

https://drive.google.com/drive/folders/13PTJLqikqikfHxQULtfidLRT134GHbn1

A pasta contém relatórios, apresentações, protocolo de bancada, resultados consolidados e cópias dos códigos principais.

## Situação final

O material necessário para consulta e continuidade do projeto está organizado entre o repositório GitHub e a pasta institucional do Google Drive.
