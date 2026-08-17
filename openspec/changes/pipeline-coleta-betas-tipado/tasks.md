## 1. Schema Protobuf e Modelagem Estática (aresta_api/)

- [ ] 1.1 TDD: Escrever testes unitários em `aresta_api/beta_proto_test.py` para validar `EscaladaAlvoBusca`, `ViasExtraidasCroqui` e os novos campos geográficos em `CandidatosBetaPorEscalada`.
- [ ] 1.2 Atualizar `aresta_api/proto/beta.proto` e recompilar stubs Python e Dart via `python aresta_api/build.py`.

## 2. Serialização e Utilitários YAML/Protobuf (coleta_de_betas/)

- [ ] 2.1 TDD: Escrever testes em `coleta_de_betas/io_yaml_test.py` para conversão bidirecional entre mensagens Protobuf e arquivos YAML com validação de esquema.
- [ ] 2.2 Implementar rotinas de serialização e desserialização tipadas em `coleta_de_betas/io_yaml.py`.

## 3. Extração de Vias do Croqui (coleta_de_betas/)

- [ ] 3.1 TDD: Escrever testes em `coleta_de_betas/extrator_vias_test.py` com dados simulados de croqui (croqui.yaml e arquivos .md).
- [ ] 3.2 Implementar `coleta_de_betas/extrator_vias.py` e CLI executável `python -m coleta_de_betas.extrair_vias` gerando `vias_extraidas.yaml`.

## 4. Runner de Busca Concorrente (coleta_de_betas/)

- [ ] 4.1 TDD: Escrever testes em `coleta_de_betas/runner_busca_test.py` com extratores mockados processando `vias_extraidas.yaml`.
- [ ] 4.2 Implementar `coleta_de_betas/runner_busca.py` e CLI executável `python -m coleta_de_betas.buscar` gerando `candidatos_brutos.yaml`.

## 5. Comando de Staging e Workflow Antigravity

- [ ] 5.1 TDD: Escrever testes em `coleta_de_betas/runner_staging_test.py` para conversão do YAML avaliado em `betas_pendentes.binarypb`.
- [ ] 5.2 Implementar `coleta_de_betas/runner_staging.py` e CLI `python -m coleta_de_betas.salvar_staging`.
- [ ] 5.3 Atualizar o workflow `.agents/workflows/coletar_betas.md` para orquestrar os comandos CLI e o disparo paralelo de sub-agentes `AvaliadorBetas`.
