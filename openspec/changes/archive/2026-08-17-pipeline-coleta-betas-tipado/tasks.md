## 1. Schema Protobuf e Modelagem Estática (aresta_api/)

- [x] 1.1 TDD (Red): Escrever testes unitários em `aresta_api/beta_proto_test.py` para validar `EscaladaAlvoBusca`, `ViasExtraidasCroqui` e os campos geográficos em `CandidatosBetaPorEscalada`.
- [x] 1.2 (Green & Refactor): Atualizar `aresta_api/proto/beta.proto` e recompilar stubs Python e Dart via `python aresta_api/build.py` garantindo que os testes passem.

## 2. Biblioteca de Serialização YAML/Protobuf (coleta_de_betas/)

- [x] 2.1 TDD (Red): Escrever testes de integração e unitários em `coleta_de_betas/io_yaml_test.py` para conversão bidirecional entre mensagens Protobuf e arquivos YAML com validação de esquema.
- [x] 2.2 (Green & Refactor): Implementar a biblioteca independente `coleta_de_betas/io_yaml.py` usando `google.protobuf.json_format`.

## 3. Biblioteca e CLI de Extração de Vias do Croqui (coleta_de_betas/)

- [x] 3.1 TDD (Red): Escrever testes de integração em `coleta_de_betas/extrator_vias_test.py` com dados de croqui (croqui.yaml e arquivos .md) validando a geração de `vias_extraidas.yaml`.
- [x] 3.2 (Green & Refactor): Implementar a biblioteca `coleta_de_betas/extrator_vias.py` e ponto de entrada CLI `coleta_de_betas/extrair_vias.py` (`python -m coleta_de_betas.extrair_vias`).

## 4. Biblioteca e CLI de Busca Concorrente de Betas (coleta_de_betas/)

- [x] 4.1 TDD (Red): Escrever testes de integração em `coleta_de_betas/runner_busca_test.py` mockando extratores para processar `vias_extraidas.yaml` e validar a saída `candidatos_brutos.yaml`.
- [x] 4.2 (Green & Refactor): Implementar a biblioteca `coleta_de_betas/runner_busca.py` e ponto de entrada CLI `coleta_de_betas/buscar.py` (`python -m coleta_de_betas.buscar`).

## 5. Biblioteca de Staging, Workflow e Validação Final

- [x] 5.1 TDD (Red): Escrever testes de integração em `coleta_de_betas/runner_staging_test.py` para conversão do YAML avaliado em `betas_pendentes.binarypb`.
- [x] 5.2 (Green & Refactor): Implementar a biblioteca `coleta_de_betas/runner_staging.py` e ponto de entrada CLI `coleta_de_betas/salvar_staging.py` (`python -m coleta_de_betas.salvar_staging`).
- [x] 5.3 Atualizar o workflow `.agents/workflows/coletar_betas.md` para orquestrar o pipeline completo e disparar sub-agentes `AvaliadorBetas` em paralelo.
- [x] 5.4 Executar suíte completa de testes (`pytest` e `python build.py`) para certificar 100% de aprovação e zero regressões.
