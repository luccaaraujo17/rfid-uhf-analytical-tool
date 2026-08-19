# Software RFID atualizado

## Correções aplicadas

- modelo real da antena: Laird PAL90209H;
- polarização: LHCP, não RHCP;
- ganho: 9 dBic;
- HPBW: 70°, não 65°;
- maior dimensão: 259,1 mm;
- distância de Fraunhofer calculada com a dimensão real;
- modelo angular limitado pela relação frente–costas de 20 dB;
- perda de descasamento calculada a partir de VSWR 1,3:1;
- tag aproximada e explicitamente paramétrica;
- orientação tridimensional por eixo dipolar;
- análise Monte Carlo de incerteza;
- comparação esperado × experimental com bias, MAE e RMSE;
- geração de entradas para openEMS.

## Aplicativos

### Aplicativo principal atualizado

```bat
streamlit run app_rfid_raio_x_fisico_pal_openems_atualizado.py
```

Mantém a interface e funcionalidades do projeto anterior, com o perfil da antena corrigido.

### Aplicativo de validação

```bat
streamlit run app_rfid_validacao_pal_openems.py
```

Use para:

- calcular link budget nominal;
- visualizar margens;
- executar Monte Carlo;
- importar CSVs do JRFID;
- comparar RSSI esperado e medido;
- aplicar apenas um offset global claramente identificado;
- exportar configuração do cenário.

## Núcleo matemático

`rfid_physics_core.py` contém:

- comprimento de onda;
- Fraunhofer;
- FSPL;
- campo elétrico em campo distante;
- ganho angular;
- VSWR/mismatch;
- enlace direto;
- enlace reverso;
- margem final;
- orientação 3D;
- Monte Carlo;
- métricas de comparação.

## Perfis JSON

- `perfis/antena_laird_pal90209h.json`
- `perfis/tag_uhf_75x20_aproximada.json`
- `perfis/ensaio_2tags_eps.json`

## Instalação

```bat
python -m pip install -r requirements_app.txt
```

## Princípio de validação

O software não deve ser alterado para reproduzir perfeitamente um único ensaio. A calibração deve usar apenas parte dos dados; outros dados, preferencialmente obtidos em nova montagem ou outro dia, devem permanecer reservados para validação independente.

## Importação de resultados openEMS

O aplicativo de validação aceita múltiplos `resultado.json`, permite escolher um cenário de referência e calcula:

- variação relativa da potência na carga por tag;
- variação relativa da RCS por cenário;
- demonstração da margem analítica corrigida;
- exportação da comparação app–openEMS.

Essas correções são relativas e devem ser usadas para estudar orientação, material e proximidade. Elas não convertem automaticamente RCS em RSSI do leitor.
