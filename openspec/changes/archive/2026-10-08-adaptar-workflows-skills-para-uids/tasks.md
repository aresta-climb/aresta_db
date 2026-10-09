# Tasks: Adaptar Workflows e Skills para UIDs Estáveis e Rótulos Semânticos

## 1. Saneamento Automático de UIDs no Pipeline Python

- [x] 1.1 Escrever testes unitários em `scripts/preparar_submissao_lib_test.py` cobrindo o saneamento idempotente de UIDs para novas entidades sem UID e a conversão de referências semânticas textuais de mapa em `corrigir_database`
- [x] 1.2 Implementar a rotina de saneamento idempotente `sanear_uids_database` em `scripts/preparar_submissao_lib.py` e integrá-la no início de `corrigir_database`, verificando a passagem dos testes criados
- [x] 1.3 Atualizar `scripts/finalizar_mapas.py` para injetar UIDs NanoID 14c em novos pontos de interesse e padronizar o campo `rotulo`, verificando com novos testes em `scripts/finalizar_mapas_test.py`

## 2. Atualização das Skills de Processamento de Croquis

- [x] 2.1 Atualizar `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` adicionando a regra de preservação estrita de UIDs existentes, a sintaxe de referências com `alvo_uid`/`pontos_uids` e o suporte a rascunho semântico
- [x] 2.2 Atualizar `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md` e `.agents/skills/mapa_corrigir_pontos_de_interesse/SKILL.md` substituindo `label` por `rotulo` e instruindo preservação de `uid` nos JSONs de metadados
- [x] 2.3 Atualizar `.agents/skills/preencher_croqui_yaml/SKILL.md` com `ultima_migracao: 5` e orientações sobre a injeção automática de UIDs pelo `deploy_generated.py`

## 3. Atualização dos Workflows de Orquestração

- [x] 3.1 Atualizar `.agents/workflows/processar_croqui_completo.md` detalhando a injeção automática de UIDs no ciclo de compilação da Fase 2 e conferência na Fase 3
- [x] 3.2 Atualizar `.agents/workflows/atualizar_croqui_completo.md` incluindo diretrizes mandatórias nos prompts dos subagentes `ConversorMarkdown` e `ExtratorMapas` para preservação integral de UIDs existentes

## 4. Validação e Testes de Regressão

- [x] 4.1 Executar a suíte completa de testes de scripts e migrações (`scripts/preparar_submissao_lib_test.py`, `scripts/finalizar_mapas_test.py`, `tests/contrato_campos_deprecados_protobuf_test.py`) e garantir 100% de cobertura
- [x] 4.2 Validar a especificação completa com `openspec validate "adaptar-workflows-skills-para-uids"` garantindo zero erros de schema
