# openEMS — guia de execução dos cenários RFID

## Estratégia adotada

A antena comercial Laird PAL90209H não foi reconstruída internamente porque os datasheets não informam patches, substratos e alimentação. O app analítico calcula o campo incidente da PAL90209H; o openEMS simula a região local da tag com onda plana normalizada.

Essa divisão permite estudar:

- influência do EPS;
- orientação frontal, horizontal e lateral;
- interação entre duas tags;
- carga elétrica paramétrica do chip;
- potência absorvida na carga;
- RCS de retroespalhamento;
- sensibilidade à malha.

## Arquivos principais

- `config_openems.json`: dimensões, materiais, carga inicial, malhas e cenários.
- `openems_common.py`: criação da tag aproximada, EPS, onda plana, probes e NF2FF.
- `00_verificar_instalacao.py`: testa importações e binários.
- `01_visualizar_geometria.py`: abre a geometria no AppCSXCAD sem executar o solver.
- `02_executar_cenario.py`: executa um cenário e cria `resultado.json`.
- `03_varredura_carga_chip.py`: varia R e C da carga aproximada.
- `04_executar_cenarios_padrao.py`: executa os cenários S0–S4.
- `05_consolidar_resultados.py`: reúne os JSONs gerados.

## Primeira execução

```bat
python 00_verificar_instalacao.py
python 01_visualizar_geometria.py --scenario S0_tag_unica_ar_frontal --mesh rapida
python 02_executar_cenario.py --scenario S0_tag_unica_ar_frontal --mesh rapida
```

Só avance se a geometria estiver correta e o solver concluir sem erro.

## Estudo de convergência

Execute o mesmo cenário com:

```bat
python 02_executar_cenario.py --scenario S1_tag_unica_eps_frontal --mesh rapida
python 02_executar_cenario.py --scenario S1_tag_unica_eps_frontal --mesh media
python 02_executar_cenario.py --scenario S1_tag_unica_eps_frontal --mesh fina
```

Compare:

- potência na carga;
- tensão e corrente;
- RCS;
- tempo e memória;
- mudança percentual entre malhas.

Resultados que ainda mudam muito com a malha não devem ser usados como conclusão.

## Carga paramétrica da tag

A tag não possui datasheet. A configuração inicial usa:

- R = 20 ohms;
- C = 1,0 pF.

Esses valores são hipóteses, não identificação do chip. Para varrer:

```bat
python 03_varredura_carga_chip.py --scenario S1_tag_unica_eps_frontal --mesh rapida
```

Use a varredura para avaliar robustez e localizar regiões de comportamento plausível em 915 MHz. Não selecione uma carga apenas porque reproduz um valor isolado da bancada.

## Escalonamento com o app

O solver fornece resultado para campo incidente normalizado de 1 V/m. O app calcula o campo real:

`K_E = E_real / 1 V/m`

- tensão e corrente escalam aproximadamente por `K_E`;
- potência absorvida e potência espalhada escalam aproximadamente por `K_E²`;
- correções relativas em dB podem ser aplicadas ao resultado analítico.

## Várias antenas virtuais

Como o leitor normalmente chaveia portas, avalie cada antena separadamente e use a maior margem disponível por ponto. Não some campos com fase fixa sem evidência de transmissão simultânea e coerente.

## Interpretação dos cenários

- S0 × S1: efeito do EPS.
- S1 × S2: efeito de proximidade e compartilhamento espacial.
- S2 × S3: efeito da orientação horizontal.
- S2 × S4: efeito da orientação lateral.
- varredura de carga: sensibilidade ao chip desconhecido.

## Saídas

Cada execução cria uma pasta em `resultados/` contendo arquivos do solver e `resultado.json`. O JSON reúne:

- cenário;
- frequência;
- R e C usados;
- RCS aproximada;
- tensão, corrente e potência na carga de cada tag;
- observações de probe.

## Limitação essencial

RSSI do JRFID APP não é diretamente igual a campo elétrico, potência na carga ou RCS. A comparação deve ser feita por tendência, deltas, limiar e, quando houver mapeamento experimental, bias/MAE/RMSE.
