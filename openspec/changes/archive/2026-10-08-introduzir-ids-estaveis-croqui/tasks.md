# Tasks: Introduzir IDs Estáveis Universais com Pure NanoID 14c

## 1. Modelagem Protobuf e Compilação dos Stubs

- [x] 1.1 Adicionar campo `croqui_uid` em `ResumoCroqui` no `aresta_api/proto/indice.proto`
- [x] 1.2 Atualizar `aresta_api/proto/croqui.proto`: adicionar `uid` em `Croqui`, `Botao`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`; adicionar `rotulo` em `PontoDeInteresse` (deprecando `label` e `id`); adicionar `alvo_uid` e `pontos_uids` em `Mapa.Referencia` (deprecando `escalada`, `setor`, `grupo`, `ids` e removendo `indice_mapa_alvo`)
- [x] 1.3 Adicionar `croqui_uid` em `aresta_api/proto/croqui_experimental.proto`
- [x] 1.4 Executar `python build.py` para gerar stubs Python e verificar que `croqui_pb2.py`, `indice_pb2.py` e `croqui_experimental_pb2.py` contêm os novos descritores e opções invisíveis
- [x] 1.5 Adicionar testes unitários em `tests/esquema_proto_test.py` validando campos, tags, tipos, remoção de `indice_mapa_alvo` e deprecação de `id` e `ids`

## 2. Suporte a Migrações Database-Only no Serving (Library-First & TDD)

- [x] 2.1 Criar testes unitários em `serving/update_serving_test.py` validando que `get_db_version()` ignora migrações que declaram `AFETA_VERSAO_SERVING = False`
- [x] 2.2 Implementar em `serving/update_serving.py` a inspeção da constante `AFETA_VERSAO_SERVING`, garantindo que a versão de serving permaneça em `v4`
- [x] 2.3 Atualizar `docs/politica_migracoes.md` documentando a convenção de migrações com escopo "database-only"

## 3. Biblioteca Pura de Gerenciamento de UIDs e URLs (Library-First & TDD)

- [x] 3.1 Criar testes unitários em `scripts/gerenciar_uids_lib_test.py` cobrindo geração de NanoID 14c Base62 via biblioteca oficial `nanoid` (`alphabet=ALFABETO_BASE62`, `size=14`), validação por regex `^[0-9a-zA-Z]{14}$`, formatação de URLs `https://aresta.cc/<uid>` e extração de UID de URLs
- [x] 3.2 Implementar `scripts/gerenciar_uids_lib.py` encapsulando a chamada `nanoid.generate` e funções puras de validação e formatação
- [x] 3.3 Verificar 100% de cobertura de testes unitários em `scripts/gerenciar_uids_lib_test.py`

## 4. Script de Migração Automática e Migração do Acervo (TDD)

- [x] 4.1 Criar testes unitários em `migracoes/0005_migrar_uids_e_rotulos_test.py` simulando croqui com formato legado (sem UIDs, com `label:`, referências com `escalada`/`setor`/`grupo`)
- [x] 4.2 Implementar `migracoes/0005_migrar_uids_e_rotulos.py` com `AFETA_VERSAO_SERVING = False`, gerando NanoIDs 14c Base62 para todas as entidades e POIs sem UID, convertendo referências de mapa para `alvo_uid`/`pontos_uids`, renomeando `label` para `rotulo` e preservando comentários com `ruamel.yaml`
- [x] 4.3 Executar a migração no banco de dados (`database/`), aplicando UIDs e novo formato em todos os croquis

## 5. Refatoração do Editor Desktop (TDD)

- [x] 5.1 Criar testes em `editor/models/croqui_model_test.py` e `editor/controllers/croqui_controller_test.py` garantindo que novas escaladas, setores, grupos e POIs recebam `uid` de 14 caracteres automaticamente
- [x] 5.2 Atualizar `CroquiModel` e serializadores do editor para gerar UIDs 14c e gravar `rotulo` em pontos de interesse (e não `label`)
- [x] 5.3 Atualizar controladores de mapas (`editor/controllers/mapas_controller.py`, `editor/views/widget_editor_mapas.py`) e comandos de histórico para manipular exclusivamente `alvo_uid` e `pontos_uids`
- [x] 5.4 Simplificar `CmdRenomearEscalada` no editor, removendo a varredura de mapas (que passam a apontar imutavelmente para `alvo_uid`), e atualizar seus testes
- [x] 5.5 Garantir que `JanelaPrincipal.carregar_croqui` em `editor/legacy_views/area_principal.py` execute `aplicar_migracoes(caminho_db)` ao abrir croquis experimentais e validar com testes

## 6. Integração no Compilador e Deploy com Retrocompatibilidade (TDD)

- [x] 6.1 Criar testes em `scripts/preparar_submissao_lib_test.py` validando que `corrigir_database` audita e valida que todas as entidades possuem UIDs de 14 caracteres válidos usando `gerenciar_uids_lib`
- [x] 6.2 Implementar em `scripts/preparar_submissao_lib.py` e `scripts/deploy_generated.py` a injeção direta de `uid`, `alvo_uid` e `pontos_uids` no Protobuf compilado, e o preenchimento em memória dos campos legados (`escalada`, `setor`, `grupo`, `label`) para retrocompatibilidade
- [x] 6.3 Atualizar testes em `scripts/deploy_generated_test.py` validando a integridade dos dados compilados e do manifesto de serving em `v4`

## 7. Testes de Contrato de Integridade do Database e do Editor (TDD)

- [x] 7.1 Criar suite de testes de contrato em `tests/contrato_database_uids_test.py` inspecionando todos os arquivos em `database/` e assertando:
  - Toda entidade possui `uid:` com exatamente 14 caracteres Base62
  - Nenhuma referência de mapa possui `escalada:`, `setor:` ou `grupo:`
  - Nenhum ponto de interesse possui o campo `label:` (deve ser estritamente `rotulo:`)
  - Não existem arquivos residuais `ids_*.yaml`
- [x] 7.2 Adicionar testes de contrato em `tests/contrato_editor_serializacao_test.py` garantindo que o editor, ao salvar croquis novos ou editados, nunca emite caminhos legados em mapas, sempre gera UIDs válidos e emite `rotulo` em vez de `label`
- [x] 7.3 Criar teste de contrato arquitetural em `tests/contrato_importacao_nanoid_test.py` inspecionando a AST de todos os módulos Python da base de código e assertando que a biblioteca externa `nanoid` nunca seja importada fora de `scripts/gerenciar_uids_lib.py`

## 8. Verificação Geral e 100% Cobertura de Testes

- [x] 8.1 Executar compilação completa com `python scripts/deploy_generated.py` e verificar que todos os croquis e o índice são gerados perfeitamente
- [x] 8.2 Executar a suíte completa de testes (`pytest`) e verificar aprovação com 100% de cobertura de código
