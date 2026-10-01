# RFID UHF - estudo de viabilidade

Repositório do projeto **Estudo de Viabilidade de Implementação de Sistema Inteligente de Identificação e Gestão Automatizada de Enxovais Hospitalares**.

O trabalho reúne software, modelagem, simulação e medições de bancada para avaliar o uso de RFID UHF passivo no controle de enxoval hospitalar do HUAC/UFCG.

## Estrutura

- `software/`: aplicação principal e núcleo de cálculos;
- `bancada/`: dados medidos, planilha-resumo e notebook de análise;
- `openems/`: scripts de simulação eletromagnética;
- `geometria/`: modelos STL usados no estudo;
- `documentos/`: figuras e materiais técnicos;
- `referencias/`: referências técnicas.

## Executar o software

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run .\software\app_rfid_raio_x_fisico_pal_openems_atualizado.py
```

Teste do núcleo:

```powershell
python .\software\testar_nucleo_matematico.py
```

## Dados de bancada

Os arquivos brutos estão em `bancada/dados/`.

Arquivos principais:

- `bancada/RESUMO_RESULTADOS_BANCADA_RFID.xlsx`
- `bancada/Analise_RFID_UHF_Graficos_Cientificos_Colab_v2.ipynb`
- `bancada/LEIA_ME_DADOS_BANCADA.txt`

Foram avaliados distância, nível nominal de FIELDSTRENGTH, presença de tecido, proximidade entre etiquetas e orientação.

Resultados consolidados usados no relatório final:

- duas etiquetas próximas: penalidade aproximada de 4,41 dB;
- toalha seca dobrada: penalidade aproximada de 6,93 dB;
- orientação lateral: penalidade aproximada de 9,04 dB.

Os resultados de bancada são a principal referência quantitativa. O modelo analítico e o openEMS foram usados como apoio à análise.

## Projeto

**Aluno:** Lucca Nunes dos Santos Pereira de Araújo  
**Curso:** Engenharia Elétrica - UFCG  
**Orientador:** Antonio Marcus Nogueira Lima  
**Coorientador:** Arthur Aprígio de Melo  
**Instituições:** UFCG / HUAC / HU Brasil

## Continuidade

Veja `ENTREGA_TECNICA.md` para um resumo dos arquivos e da organização final do projeto.
