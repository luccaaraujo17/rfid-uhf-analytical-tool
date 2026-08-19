\# RFID UHF Analytical Tool



Ferramenta computacional desenvolvida para análise, pré-dimensionamento e apoio à avaliação de viabilidade técnica de sistemas RFID UHF passivos.



O projeto foi desenvolvido no contexto de uma pesquisa de Iniciação Científica aplicada à identificação e rastreabilidade de enxovais hospitalares no Hospital Universitário Alcides Carneiro (HUAC), da Universidade Federal de Campina Grande (UFCG).



\## Objetivo



A ferramenta auxilia a análise física do enlace RFID UHF e a investigação dos principais fatores que influenciam a confiabilidade de leitura de etiquetas RFID em aplicações reais.



Entre as grandezas e fenômenos analisados estão:



\- comprimento de onda;

\- região de campo distante;

\- EIRP;

\- perdas de propagação em espaço livre;

\- enlace leitor–etiqueta RFID;

\- limiar de ativação da etiqueta RFID;

\- enlace reverso por backscatter;

\- margens de leitura;

\- orientação da etiqueta RFID;

\- perdas adicionais;

\- influência da distância e de materiais;

\- proximidade entre etiquetas RFID;

\- comparação com resultados experimentais.



\## Estrutura do projeto



```text

software/    aplicação principal, núcleo físico e ferramentas auxiliares

openems/     scripts para modelagem e simulação eletromagnética

bancada/     dados e ferramentas de análise dos ensaios experimentais

geometria/   modelos tridimensionais utilizados no estudo

documentos/  figuras e protocolos produzidos durante a pesquisa

