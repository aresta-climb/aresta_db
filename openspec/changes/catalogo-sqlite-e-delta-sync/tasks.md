# Tasks

## 1. Biblioteca de Geração do Catálogo SQLite

- [ ] 1.1 Criar suíte de testes unitários `scripts/gerar_catalogo_sqlite_lib_test.py` cobrindo a criação das tabelas `catalogo_croquis` e `catalogo_aresta`, criação de índices e extração de dados de croquis e escaladas
- [ ] 1.2 Implementar `scripts/gerar_catalogo_sqlite_lib.py` com as funções de inicialização de esquema, extração de dados de croqui compilado e inserção no banco, validando que os testes passam
- [ ] 1.3 Adicionar testes e suporte para substituição atômica seletiva por `croqui_uid` (deploy parcial) e compactação gzip (`catalogo.db.gz`), garantindo 100% de cobertura de código

## 2. Integração no Pipeline de Deploy

- [ ] 2.1 Adicionar casos de teste em `scripts/deploy_generated_test.py` para validar a execução do Passo E (geração do catálogo SQLite e gzip) em deploy total e seletivo
- [ ] 2.2 Integrar a execução do Passo E em `scripts/deploy_generated.py` e registrar as entradas `catalogo.db` e `catalogo.db.gz` com seus hashes SHA-256 no manifesto `passo_d_gerar_manifesto_serving`
- [ ] 2.3 Executar deploy de validação em ambiente de teste e verificar a integridade estrutural do `catalogo.db` e as entradas em `arquivos_serving.yaml`

## 3. Utilitário de Deltas para Cloudflare D1

- [ ] 3.1 Criar suíte de testes unitários `scripts/gerar_deltas_catalogo_test.py` cobrindo comparação SQL de duas instâncias do catálogo via `EXCEPT` (detectando adições, alterações e remoções de croquis e vias)
- [ ] 3.2 Implementar `scripts/gerar_deltas_catalogo.py` produzindo changeset estruturado (`upserts` e `deletes`) serializado para inserção na tabela `deltas_catalogo` do Cloudflare D1
- [ ] 3.3 Validar 100% de cobertura de testes unitários para a extração de deltas

## 4. Documentação e Validação Final

- [ ] 4.1 Documentar o contrato do Cloudflare Worker (`aresta.cc`) para as rotas `/sync?desde=X` e `/:uid` com exemplos de queries e resposta em `docs/catalogo_sqlite_e_delta_sync.md`
- [ ] 4.2 Executar suíte completa de testes do repositório garantindo que nenhum teste existente foi quebrado
