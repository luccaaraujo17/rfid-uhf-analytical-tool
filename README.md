# RFID UHF Analytical Tool

Ferramenta computacional para análise física, pré-dimensionamento e apoio à avaliação de viabilidade técnica de sistemas RFID UHF passivos.

Desenvolvida no contexto de pesquisa de Iniciação Científica aplicada à identificação e rastreabilidade de enxovais hospitalares no Hospital Universitário Alcides Carneiro (HUAC), vinculado à Universidade Federal de Campina Grande (UFCG).

> **Status:** versão acadêmica de pesquisa — 2026.

---

## Visão geral

O RFID UHF Analytical Tool foi desenvolvido para auxiliar a investigação de sistemas RFID UHF por meio da integração entre:

- modelagem física e cálculo analítico;
- desenvolvimento de software;
- análise do enlace RFID;
- modelagem tridimensional;
- simulação eletromagnética com openEMS;
- ensaios experimentais de bancada;
- análise de dados experimentais.

Os resultados experimentais de bancada constituem a principal referência quantitativa do estudo. Os modelos analíticos e as simulações são empregados como ferramentas complementares de interpretação e pré-dimensionamento.

## Funcionalidades

A ferramenta permite estudar parâmetros e fenômenos relacionados a:

- comprimento de onda;
- região de campo distante;
- EIRP;
- perda de propagação em espaço livre;
- enlace direto leitor–etiqueta RFID;
- limiar de ativação da etiqueta RFID;
- enlace reverso por backscatter;
- margem de leitura;
- perdas adicionais;
- influência da orientação;
- influência da distância;
- influência de materiais têxteis;
- proximidade entre etiquetas RFID;
- comparação entre previsão analítica e resultados experimentais.

## Arquitetura do projeto

```text
software/
    Aplicação principal, núcleo físico e ferramentas auxiliares.

openems/
    Scripts para preparação, execução e análise de simulações eletromagnéticas.

bancada/
    Dados experimentais, notebook de análise e resultados consolidados.

geometria/
    Modelos tridimensionais utilizados no estudo.

documentos/
    Figuras próprias e template de registro experimental.

docs/
    Documentação complementar e screenshots.
```

## Metodologia

O desenvolvimento seguiu uma arquitetura metodológica composta por:

1. revisão bibliográfica;
2. levantamento das características da aplicação;
3. modelagem física do enlace RFID UHF;
4. desenvolvimento da ferramenta analítica;
5. modelagem tridimensional;
6. simulação eletromagnética complementar;
7. ensaios experimentais;
8. processamento dos dados;
9. interpretação dos resultados;
10. elaboração de diretrizes para aplicação.

A bancada experimental foi utilizada para verificar o comportamento do sistema em condições controladas e investigar fatores relevantes ao dimensionamento da solução.

## Ensaios experimentais

Foram investigados, entre outros fatores:

- distância entre antena e etiqueta RFID;
- diferentes níveis de configuração de leitura;
- presença de material têxtil;
- orientação da etiqueta RFID;
- proximidade entre duas etiquetas RFID;
- completude do inventário;
- comportamento do RSSI;
- robustez em diferentes condições experimentais.

Os ensaios foram concebidos para isolar fenômenos relevantes ao dimensionamento do sistema, não para representar uma implantação hospitalar definitiva.

## Principais resultados experimentais

Nas condições avaliadas, observou-se inventário completo em configurações favoráveis até 200 cm.

Os experimentos também evidenciaram penalidades relativas associadas a condições críticas, incluindo aproximadamente:

- **4,41 dB** para duas etiquetas RFID próximas;
- **6,93 dB** para a presença de toalha seca dobrada;
- **9,04 dB** para orientação lateral.

Esses resultados demonstram que distância, material, proximidade e orientação devem ser considerados no dimensionamento de uma zona de leitura RFID UHF.

## Software analítico

A aplicação principal encontra-se em:

```text
software/app_rfid_raio_x_fisico_pal_openems_atualizado.py
```

O núcleo matemático está concentrado em:

```text
software/rfid_physics_core.py
```

## Instalação

Recomenda-se a utilização de ambiente virtual Python.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Executando a aplicação

```powershell
streamlit run .\software\app_rfid_raio_x_fisico_pal_openems_atualizado.py
```

O Streamlit abrirá a interface da ferramenta no navegador.

## Verificação do núcleo matemático

```powershell
python .\software\testar_nucleo_matematico.py
```

## openEMS

O diretório `openems/` reúne os scripts utilizados na preparação, execução e pós-processamento dos cenários eletromagnéticos.

O openEMS é uma dependência externa e seus binários não são distribuídos neste repositório.

As simulações são utilizadas como ferramenta complementar de análise. Os resultados experimentais permanecem como referência quantitativa principal.

## Dados experimentais

O diretório `bancada/dados/` contém os arquivos provenientes dos ensaios realizados durante a pesquisa.

O notebook:

```text
bancada/Analise_RFID_UHF_Graficos_Cientificos_Colab_v2.ipynb
```

foi utilizado no processamento e na geração de visualizações científicas dos resultados.

## Geometrias

O diretório `geometria/` contém representações tridimensionais utilizadas no estudo, incluindo:

- envelope da antena;
- suporte de EPS;
- geometria aproximada da etiqueta RFID;
- configuração experimental com duas etiquetas RFID.

## Reprodutibilidade

O repositório inclui:

- núcleo matemático;
- scripts de simulação;
- parâmetros utilizados;
- geometrias;
- dados experimentais;
- notebook de processamento;
- gráficos científicos;
- template de registro de bancada.

Essa organização busca favorecer a rastreabilidade das etapas computacionais e experimentais da pesquisa.

## Limitações

A ferramenta é destinada ao apoio à análise e ao pré-dimensionamento.

Resultados analíticos ou simulados não substituem:

- ensaios experimentais;
- caracterização dos componentes;
- análise de repetibilidade;
- validação da zona de leitura;
- ensaios em escala operacional;
- validação no ambiente final de aplicação.

A seleção definitiva de leitores, antenas, etiquetas RFID e infraestrutura deve considerar as características específicas de cada implantação.

## Contexto acadêmico

Software desenvolvido no contexto do projeto:

**Estudo de Viabilidade de Implementação de Sistema Inteligente de Identificação e Gestão Automatizada de Enxovais Hospitalares**

**Instituições:**  
Universidade Federal de Campina Grande — UFCG  
Hospital Universitário Alcides Carneiro — HUAC / HU Brasil

**Desenvolvimento:**  
Lucca Araújo — Engenharia Elétrica/UFCG

**Orientação:**  
Antonio Marcus Nogueira Lima

## Citação

As informações para citação acadêmica estão disponíveis no arquivo `CITATION.cff`.

## Licenciamento

O código-fonte encontra-se publicamente disponível para fins acadêmicos e de transparência científica.

A licença definitiva de reutilização e distribuição será definida após a conclusão dos procedimentos institucionais pertinentes.

## Versão

**v1.0.0 — versão acadêmica inicial, 2026.**
