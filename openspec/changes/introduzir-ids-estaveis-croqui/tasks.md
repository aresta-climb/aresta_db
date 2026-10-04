# Tasks: Introduzir IDs Estáveis para Croquis e Entidades

## 1. Modelagem Protobuf e Compilação dos Stubs

- [ ] 1.1 Adicionar campos `proximo_id` e `id_numerico` invisíveis em `aresta_api/proto/indice.proto` e verificar compilação sintática
- [ ] 1.2 Adicionar campos `id_numerico` e `proximo_id` em `Croqui`, `id` em `Grupo`, `Setor`, `Escalada`, e `alvo_id` em `Mapa.Referencia` (marcando `escalada`, `setor`, `grupo` como deprecados) em `aresta_api/proto/croqui.proto` e verificar compilação sintática
- [ ] 1.3 Executar `python build.py` para gerar os stubs Python e verificar que `croqui_pb2.py` e `indice_pb2.py` contêm os novos descritores e opções invisíveis
- [ ] 1.4 Adicionar testes unitários em `tests/test_proto_schema.py` validando os números de tags, extensões `formato_na_ui = INVISIVEL` e deprecações

## 2. Biblioteca de Lookup e Resolução de Entidades por ID (Library-First)

- [ ] 2.1 Criar teste unitário `editor/models/identificadores_util_test.py` com casos para indexação em memória, busca $O(1)$ por ID folha e extração de ancestrais (setor pai e grupo pai)
- [ ] 2.2 Implementar biblioteca `editor/models/identificadores_util.py` com funções para construir o mapa de lookup reativo `Map[int, ResolucaoEntidade]` e resolver referências a partir de `alvo_id`
- [ ] 2.3 Garantir 100% de cobertura de testes em `editor/models/identificadores_util_test.py`

## 3. Geração de IDs e Comandos no Editor (Undo/Redo & TDD)

- [ ] 3.1 Criar testes em `editor/controllers/croqui_controller_test.py` para garantir que criação de nova escalada, setor ou grupo receba `croqui.proximo_id` e incremente o contador
- [ ] 3.2 Criar testes em `editor/commands/comandos_protobuf_test.py` garantindo que a operação de Undo remova a entidade criada sem decrementar `croqui.proximo_id` (monotonicidade estrita)
- [ ] 3.3 Implementar a injeção automática de `id` consumindo `croqui.proximo_id` nos controladores de criação de entidades em `editor/controllers/croqui_controller.py`
- [ ] 3.4 Atualizar `editor/controllers/mapas_controller.py` e seus testes (`mapas_controller_test.py`) para gravar primariamente `alvo_id` ao criar ou associar referências de traçados

## 4. Migração Sequencial do Acervo Existente (TDD)

- [ ] 4.1 Criar teste unitário `migracoes/0005_atribuir_ids_estaveis_test.py` simulando um croqui com entidades e mapas antigos sem IDs
- [ ] 4.2 Implementar a migração `migracoes/0005_atribuir_ids_estaveis.py` que ordena croquis alfabeticamente no índice, atribui `id_numerico = 1..N`, gera `id = 1..M` para entidades locais e preenche `alvo_id` em todos os mapas
- [ ] 4.3 Executar a migração sobre os croquis do `database/` via `scripts/migrador.py` e verificar que todos os arquivos `.md` e `croqui.yaml` receberam os IDs de forma determinística

## 5. Compilador, Validador e Retrocompatibilidade (TDD)

- [ ] 5.1 Criar testes em `scripts/preparar_submissao_lib_test.py` validando que `corrigir_database` detecta entidades sem ID inseridas manualmente e atribui `croqui.proximo_id`
- [ ] 5.2 Implementar guardião de integridade e preenchimento de strings legadas (`escalada`, `setor`, `grupo`) a partir de `alvo_id` na rotina de compilação de `scripts/preparar_submissao_lib.py`
- [ ] 5.3 Criar testes em `scripts/deploy_generated_test.py` validando a gestão do `proximo_id` global no índice e a persistência de `id_numerico` no `indice.yaml`
- [ ] 5.4 Atualizar `scripts/deploy_generated.py` para garantir atribuição e preservação imutável de IDs no `indice.yaml` e `indice.binarypb`

## 6. Testes de Integração e Verificação Geral

- [ ] 6.1 Executar teste de integração executando `python scripts/deploy_generated.py` e verificando que o índice e os croquis compilados são gerados sem warnings ou erros
- [ ] 6.2 Executar a suíte completa de testes (`pytest`) e verificar que todos os testes passam com 100% de cobertura
