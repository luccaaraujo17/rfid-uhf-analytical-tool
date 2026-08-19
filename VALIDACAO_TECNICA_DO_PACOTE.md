# Validação técnica realizada antes da entrega

## Verificações executadas

- compilação sintática de todos os arquivos Python em `software/` e `openems/`;
- execução de `software/testar_nucleo_matematico.py`;
- validação de todos os arquivos JSON;
- conferência automática das dimensões dos STLs;
- confirmação de que os STLs são fechados após processamento geométrico;
- busca por valores antigos de RHCP, HPBW 65° e dimensão 0,26 m nos presets ativos;
- renderização do documento técnico em páginas PNG;
- inspeção visual de capa, fluxograma, equações, tabelas, gráficos, manifesto e referências;
- exportação do documento técnico para PDF;
- criação de planilha-resumo dos dados de bancada.

## Verificações que dependem do computador Windows do usuário

- importação efetiva dos wheels CSXCAD/openEMS;
- abertura do XML no AppCSXCAD;
- execução FDTD com malha rápida;
- geração dos dumps HDF5 e NF2FF;
- estudo de convergência nas malhas média e fina.

## Critério de aceitação da primeira execução

1. `00_verificar_instalacao.py` deve terminar com `INSTALAÇÃO FUNCIONAL`.
2. `01_visualizar_geometria.py` deve abrir o cenário sem sobreposição indevida.
3. S0 deve finalizar e gerar `resultado.json`.
4. S1 e S2 devem produzir potência na carga e RCS finitas.
5. Os resultados devem permanecer qualitativamente coerentes ao refinar a malha.
