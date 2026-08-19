# Parâmetros e hipóteses oficiais

## Antena PAL90209H - confirmados por datasheet

| Parâmetro | Valor |
|---|---:|
| Faixa | 902-928 MHz |
| Frequência nominal | 915 MHz |
| Ganho | 9 dBic |
| Polarização | LHCP |
| HPBW azimute | 70° |
| Frente-costas | 20 dB |
| VSWR máximo | 1,3:1 |
| Razão axial típica | 1 dB |
| Impedância | 50 ohms |
| Dimensões | 259,1 x 259,1 x 33,5 mm |
| Conector | N-fêmea fixo |

## Tag aproximada - não confirmada

| Parâmetro | Valor inicial/status |
|---|---|
| Tipo | UHF passiva adesiva |
| Dimensões | 75 x 20 mm |
| Polarização | linear |
| Ganho inicial | 0 dBi |
| Sensibilidade inicial | -18 dBm |
| Carga inicial | elemento RC paramétrico: 20 ohms e 1,0 pF |
| Varredura inicial | R = 10, 20, 30, 40 ohms; C = 0,7, 1,0, 1,3, 1,7 pF |
| Chip | desconhecido |
| Geometria | meandriforme aproximada baseada em fotografia |

A topologia exata equivalente da carga depende do modelo do chip. Os valores servem para análise paramétrica, não para identificação do componente.

## EPS do ensaio

| Parâmetro | Valor |
|---|---:|
| Largura | 335 mm |
| Altura | 295 mm |
| Espessura | 30 mm |
| epsilon_r inicial | 1,05 |
| Condutividade inicial | 0 S/m |
| Tag 1 | centro a 100 mm da base |
| Tag 2 | centro a 155 mm da base |
| Separação | 55 mm |

## Toalha seca dobrada

As propriedades não foram medidas. O solver usa varredura, não um valor universal:

- espessura: 10, 20 e 30 mm;
- epsilon_r: 1,2; 1,6; 2,0;
- condutividade: 0,005; 0,02; 0,05 S/m.

A faixa é uma hipótese de engenharia para análise de sensibilidade e deve ser refinada quando houver caracterização.

## Hipóteses de enlace

- campo distante a partir de aproximadamente 0,410 m;
- perda CP-LP nominal de 3 dB entre PAL circular e tag linear;
- ganho angular parabólico aproximado com HPBW de 70° e limite de 20 dB;
- perda de mismatch da PAL calculada a partir de VSWR 1,3:1;
- cabo, backscatter, sensibilidade da tag e leitor permanecem calibráveis;
- openEMS opera localmente com onda plana linear normalizada;
- o app trata distância, potência, ganho e padrão da antena real;
- correções openEMS são relativas ao cenário S0.

## Dados experimentais

Os valores medidos variam com remontagem, conectores, cabo, posição, ambiente, multipercurso, lote da tag e algoritmo do leitor. Eles devem ser armazenados com metadados e usados para comparação, não convertidos diretamente em constantes universais.
