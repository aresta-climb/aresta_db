# Tasks: Introduzir IDs Estáveis para Croquis e Entidades

## 1. Modelagem Protobuf e Compilação dos Stubs

- [ ] 1.1 Adicionar campo `croqui_id_numerico` (Nível 1 - Global) em `ResumoCroqui` no `aresta_api/proto/indice.proto` (sem campo contador no catálogo)
- [ ] 1.2 Atualizar `aresta_api/proto/croqui.proto`: adicionar `uid` e `id` (`entidade_id_numerico`, Nível 2) em `Croqui`, `Grupo`, `Setor`, `Escalada`; adicionar `uid` e `id` (`ponto_id_numerico`, Nível 3) e `rotulo` em `PontoDeInteresse` (deprecando `label`); adicionar `alvo_uid`, `pontos_uids`, `alvo_id` (`entidade_id_numerico`) e `pontos_ids` (`ponto_id_numerico`) em `Mapa.Referencia` (deprecando `escalada`, `setor`, `grupo`)
- [ ] 1.3 Adicionar `croqui_id_numerico` e `croqui_uid` em `aresta_api/proto/croqui_experimental.proto`
- [ ] 1.4 Executar `python build.py` para gerar stubs Python e verificar que `croqui_pb2.py`, `indice_pb2.py` e `croqui_experimental_pb2.py` contêm os novos descritores e opções invisíveis
- [ ] 1.5 Adicionar testes unitários em `tests/test_proto_schema.py` validando campos, tags, tipos e extensões `formato_na_ui = INVISIVEL`

## 2. Suporte a Migrações Database-Only no Serving (Library-First & TDD)

- [ ] 2.1 Criar testes unitários em `serving/update_serving_test.py` validando que `get_db_version()` ignora migrações que declaram `AFETA_VERSAO_SERVING = False`
- [ ] 2.2 Implementar em `serving/update_serving.py` a inspeção da constante `AFETA_VERSAO_SERVING`, garantindo que a versão de serving permaneça em `v4`
- [ ] 2.3 Atualizar `docs/politica_migracoes.md` documentando a convenção de migrações com escopo "database-only"

## 3. Biblioteca de Gerenciamento de IDs Numéricos em Três Níveis (Library-First & TDD)

- [ ] 3.1 Criar testes unitários em `scripts/gerenciar_ids_numericos_lib_test.py` cobrindo geração/validação de NanoID Base62 12c (`xxxx-xxxx-xxxx`), alocação de IDs inteiros livres nos três níveis (`croqui_id_numerico`, `entidade_id_numerico`, `ponto_id_numerico`) sem exigir contiguidade e I/O de arquivos YAML
- [ ] 3.2 Criar testes unitários em `scripts/gerenciar_ids_numericos_lib_test.py` para o algoritmo de resolução semântica de conflitos de merge (técnica de split de visões HEAD vs. Conflitante)
- [ ] 3.3 Implementar `scripts/gerenciar_ids_numericos_lib.py` com gerador de UIDs, classes `TabelaIdsLocais` (`entidade_id_numerico` e `ponto_id_numerico`) e `TabelaIdsGlobais` (`croqui_id_numerico`), e função pura de resolução de conflitos sem dependência de Git
- [ ] 3.4 Verificar 100% de cobertura de testes unitários em `scripts/gerenciar_ids_numericos_lib_test.py`

## 4. Script de Migração Automática e Migração do Acervo (TDD)

- [ ] 4.1 Criar testes unitários em `migracoes/0005_migrar_uids_e_rotulos_test.py` simulando croqui com formato legado (sem UIDs, com `label:`, referências com `escalada`/`setor`/`grupo`)
- [ ] 4.2 Implementar `migracoes/0005_migrar_uids_e_rotulos.py` com `AFETA_VERSAO_SERVING = False`, gerando UIDs, criando `ids_entidades.yaml` (`entidade_id_numerico`) e `ids_pontos.yaml` (`ponto_id_numerico`), convertendo referências de mapa para `alvo_uid`/`pontos_uids`, renomeando `label` para `rotulo` e preservando comentários com `ruamel.yaml`
- [ ] 4.3 Criar script auxiliar `scripts/migrar_uids_database.py` e testes associados para migrar o acervo completo e gerar `database/ids_globais.yaml` (`croqui_id_numerico`)
- [ ] 4.4 Executar a migração no banco de dados (`database/`), gerando `ids_globais.yaml`, `ids_entidades.yaml` e `ids_pontos.yaml` para todos os croquis

## 5. Refatoração do Editor Desktop (TDD)

- [ ] 5.1 Criar testes em `editor/core/croqui_model_test.py` e `editor/controllers/croqui_controller_test.py` garantindo que novas escaladas, setores e grupos recebam `uid` automaticamente e não gravem `id` direto
- [ ] 5.2 Atualizar `CroquiModel` e serializadores do editor para gerar UIDs e gravar `rotulo` em pontos de interesse (e não `label`)
- [ ] 5.3 Atualizar controladores de mapas (`editor/controllers/mapas_controller.py`, `editor/views/widget_editor_mapas.py`) e comandos de histórico para manipular exclusivamente `alvo_uid` e `pontos_uids`
- [ ] 5.4 Simplificar `CmdRenomearEscalada` no editor, removendo a varredura de mapas (que passam a apontar imutavelmente para `alvo_uid`), e atualizar seus testes
- [ ] 5.5 Garantir que `JanelaPrincipal.carregar_croqui` em `editor/legacy_views/area_principal.py` execute `aplicar_migracoes(caminho_db)` ao abrir croquis experimentais e validar com testes

## 6. Integração no Compilador e Deploy (TDD)

- [ ] 6.1 Criar testes em `scripts/preparar_submissao_lib_test.py` validando que `corrigir_database` audita e aloca UIDs/IDs faltantes nos três níveis usando a `gerenciar_ids_numericos_lib`
- [ ] 6.2 Implementar em `scripts/preparar_submissao_lib.py` a tradução de UIDs para IDs numéricos compactos (`alvo_id` $\rightarrow$ `entidade_id_numerico`, `pontos_ids` $\rightarrow$ `ponto_id_numerico`), o preenchimento de campos legados (`escalada`, `setor`, `grupo`, `label`) e a omissão de UIDs no `.binarypb` final
- [ ] 6.3 Criar testes em `scripts/deploy_generated_test.py` validando o gerenciamento de `ids_globais.yaml` (`croqui_id_numerico`) e a geração do manifesto de serving
- [ ] 6.4 Atualizar `scripts/deploy_generated.py` para consumir a biblioteca de IDs e validar a integridade de dados compilados

## 7. Testes de Contrato de Integridade do Database e do Editor (TDD)

- [ ] 7.1 Criar suite de testes de contrato em `tests/contrato_database_uids_test.py` inspecionando todos os arquivos em `database/` e assertando:
  - Nenhuma entidade possui o campo `id:` direto (permitido exclusivamente nos arquivos `ids_*.yaml`)
  - Nenhuma referência de mapa possui `escalada:`, `setor:` ou `grupo:`
  - Nenhum ponto de interesse possui o campo `label:` (deve ser estritamente `rotulo:`)
- [ ] 7.2 Adicionar testes de contrato em `tests/contrato_editor_serializacao_test.py` garantindo que o editor, ao salvar croquis novos ou editados, nunca emite `id` direto nas entidades, nunca emite caminhos legados em mapas e emite `rotulo` em vez de `label`

## 8. Verificação Geral e 100% Cobertura de Testes

- [ ] 8.1 Executar compilação completa com `python scripts/deploy_generated.py` e verificar que todos os croquis e o índice são gerados perfeitamente
- [ ] 8.2 Executar a suíte completa de testes (`pytest`) e verificar aprovação com 100% de cobertura de código
