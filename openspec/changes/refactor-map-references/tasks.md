## 1. Atualização do Schema Protobuf (TDD não se aplica a schemas, mas a validação sim)

- [ ] 1.1 Remover campos `id_no_mapa` de `Grupo` e `Setor` no `croqui.proto`
- [ ] 1.2 Remover campos `id_no_mapa`, `id_no_mapa_meio` e `id_no_mapa_fim` das variações de `Escalada` no `croqui.proto`
- [ ] 1.3 Adicionar as mensagens `Referencia` e `AjusteDeCamera` no escopo da mensagem `Mapa`
- [ ] 1.4 Adicionar o campo `referencias` (repeated Referencia) na mensagem `Mapa`
- [ ] 1.5 Rodar compilação do Protobuf para atualizar bindings

## 2. Documentação da Política de Migração

- [ ] 2.1 Criar/Atualizar `docs/politica_migracoes.md` (em português) definindo o padrão de criação de scripts Python na pasta `migracoes`, exigindo TDD e 100% de test coverage para todos os scripts de migração

## 3. TDD: Testes de Migração (Inegociável: 100% Coverage)

- [ ] 3.1 Criar o arquivo de teste `aresta_db/migracoes/0002_centralizar_map_references_test.py`
- [ ] 3.2 Implementar testes unitários e de integração que validem a extração correta dos IDs antigos (simulando YAMLs com e sem as chaves)
- [ ] 3.3 Implementar testes que validem a injeção da lista `referencias` no mapa correto
- [ ] 3.4 Rodar os testes e garantir que eles falham (Red)

## 4. Implementação do Script de Migração de Dados (Library-First & Simplicidade)

- [ ] 4.1 Criar o script `aresta_db/migracoes/0002_centralizar_map_references.py` usando `ruamel.yaml`
- [ ] 4.2 Implementar as funções de migração para fazer os testes passarem (Green)
- [ ] 4.3 Refatorar o código mantendo a simplicidade e declaratividade (Refactor)
- [ ] 4.4 Verificar a cobertura de testes do script usando `pytest --cov=aresta_db/migracoes/0002_centralizar_map_references.py` e garantir 100% de coverage
- [ ] 4.5 Executar o script em toda a base de dados
- [ ] 4.6 Revisar manualmente as alterações no git (ex: `br_mg_ouro_preto_ouroboulder.yaml`)

## 5. Validação Final

- [ ] 5.1 Executar a suíte de testes completa do repositório para garantir que nenhum croqui migrado contenha erros de schema
