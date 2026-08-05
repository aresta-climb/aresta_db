## 1. Atualização dos Protobufs

- [x] 1.1 Adicionar `total_esportivas`, `total_moveis`, `total_boulders`, `total_multiplas_enfiadas`, `total_highlines` (como int32) em `PrecomputadosSetor`, `PrecomputadosGrupo` e `PrecomputadosPico` (`aresta_api/proto/croqui.proto`)
- [x] 1.2 Adicionar os mesmos campos em `PrecomputadosResumoCroqui` (`aresta_api/proto/indice.proto`)
- [x] 1.3 Executar script de build dos protos (`build.py protos`) no aresta_api para regerar os binds em Python e Dart

## 2. Lógica de Agregação (Precomputados)

- [x] 2.1 Modificar `computar_precomputados_setor` em `scripts/preparar_submissao_lib.py` para detectar a chave do `tipo` de cada escalada e somar os valores nos contadores do nó do Setor
- [x] 2.2 Modificar `computar_precomputados_grupo` e `computar_precomputados_pico` para iterar as keys `total_*` dos filhos e fazer o roll-up 
- [x] 2.3 Atualizar testes em `scripts/preparar_submissao_lib_test.py` para validar a extração correta dos tipos mistos e do fluxo vazio (0)

## 3. Índice e Testes 

- [x] 3.1 Atualizar `passo_c_gerar_indice` em `scripts/deploy_generated.py` para fazer roll-up dos novos contadores dos Picos e injetar no `ResumoCroqui`
- [x] 3.2 Incluir a serialização opcional condicional no `indice_list` de `deploy_generated.py` apenas para as chaves maiores que 0 (para o debug via `indice.yaml`)
- [x] 3.3 Adicionar assertions sobre os novos contadores no `scripts/deploy_generated_test.py`

## 4. Validação End-to-End

- [x] 4.1 Rodar pytest validando todas as rotinas
- [x] 4.2 Gerar todos os dados locais usando o pipeline principal e assegurar que as marcações não vazam `0` nos arquivos .yaml gerados.
