## 1. Atualização do Schema Protobuf (TDD não se aplica a schemas, mas a validação sim)

- [x] 1.1 Remover campos `id_no_mapa` de `Grupo` e `Setor` no `croqui.proto`
- [x] 1.2 Remover campos `id_no_mapa`, `id_no_mapa_meio` e `id_no_mapa_fim` das variações de `Escalada` no `croqui.proto`
- [x] 1.3 Adicionar as mensagens `Referencia` e `AjusteDeCamera` no escopo da mensagem `Mapa`
- [x] 1.4 Documentar extensivamente e detalhadamente os novos campos em `Referencia` e `AjusteDeCamera` usando comentários Protobuf (explicando a geometria infinita, o cross-linking e as porcentagens da câmera)
- [x] 1.5 Adicionar o campo `referencias` (repeated Referencia) na mensagem `Mapa`
- [x] 1.6 Rodar compilação do Protobuf para atualizar bindings

## 2. Ajuste dos Agentes e Workflows (Processamento de Croqui)

- [x] 2.1 Modificar a skill `@converter_parte_croqui_para_markdown` para instruir o agente a extrair e estruturar as referências de escaladas diretamente no array `referencias` dos mapas, e não mais nas escaladas
- [x] 2.2 Modificar a skill `@preencher_croqui_yaml` para que o sub-agente saiba compilar e validar essa nova estrutura de ligações (referências)
- [x] 2.3 Revisar o workflow `processar_croqui_completo.md` se necessário, para alinhar com o novo formato de extração da Fase 2

## 3. Documentação da Política de Migração

- [x] 3.1 Criar/Atualizar `docs/politica_migracoes.md` (em português) definindo o padrão de criação de scripts Python na pasta `migracoes`, exigindo TDD e 100% de test coverage para todos os scripts de migração

## 4. TDD: Testes de Migração (Inegociável: 100% Coverage)

- [x] 4.1 Criar o arquivo de teste `aresta_db/migracoes/0002_centralizar_map_references_test.py`
- [x] 4.2 Implementar testes unitários e de integração que validem a extração correta dos IDs antigos (simulando YAMLs com e sem as chaves)
- [x] 4.3 Implementar testes que validem a injeção da lista `referencias` no mapa correto
- [x] 4.4 Rodar os testes e garantir que eles falham (Red)

## 5. Implementação do Script de Migração de Dados (Library-First & Simplicidade)

- [x] 5.1 Criar o script `aresta_db/migracoes/0002_centralizar_map_references.py` usando `ruamel.yaml`
- [x] 5.2 Implementar as funções de migração para fazer os testes passarem (Green)
- [x] 5.3 Refatorar o código mantendo a simplicidade e declaratividade (Refactor)
- [x] 5.4 Verificar a cobertura de testes do script usando `pytest --cov=aresta_db/migracoes/0002_centralizar_map_references.py` e garantir 100% de coverage
- [x] 5.5 Executar o script em toda a base de dados
- [x] 5.6 Revisar manualmente as alterações no git (ex: `br_mg_ouro_preto_ouroboulder.yaml`)

## 6. Validação Final

- [x] 6.1 Executar a suíte de testes completa do repositório para garantir que nenhum croqui migrado contenha erros de schema
