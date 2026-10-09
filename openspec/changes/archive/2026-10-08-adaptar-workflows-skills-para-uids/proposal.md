# Proposal: Adaptar Workflows e Skills para UIDs Estáveis e Rótulos Semânticos

## Why

Com a introdução dos identificadores universais NanoID 14c (`uid`) e rótulos semânticos (`rotulo`) na versão 5 do schema de dados, os workflows e skills dos agentes autônomos (`.agents/skills/` e `.agents/workflows/`) permaneceram instruindo a criação de arquivos Markdown e JSON no formato legado (`label`, `escalada: 'Nome'`, `ids: [...]`, sem `uid`). Além disso, o script de preparação e compilação (`corrigir_database` / `deploy_generated.py`) dependia do incremento linear do número de versão de migração em `croqui.yaml`, impedindo a injeção automática de UIDs em croquis novos ou mapas recém-extraídos e quebrando a validação com erro de auditoria.

## What Changes

- **Saneamento Contínuo e Idempotente de UIDs no Pipeline**: Modifica `scripts/preparar_submissao_lib.py` para invocar a rotina de saneamento de UIDs e conversão de referências de mapa durante `corrigir_database`, garantindo que qualquer entidade nova (setor, grupo, escalada, ponto de interesse, botão ou croqui) receba um NanoID 14c válido e referências semânticas sejam convertidas para `alvo_uid` e `pontos_uids`, independente do campo `ultima_migracao` em `croqui.yaml`.
- **Preservação de UIDs em `finalizar_mapas.py`**: Garante que o script de finalização de mapas atribua ou preserve UIDs estáveis para novos pontos de interesse e respeite a nomenclatura de `rotulo`.
- **Atualização da Skill `converter_parte_croqui_para_markdown`**: Instruções para preservação estrita de UIDs em arquivos existentes, esclarecimento de que novas escaladas/setores podem ser rascunhados sem UID (gerado via pipeline), e atualização da sintaxe canônica de referências para `alvo_uid` e `pontos_uids` (com suporte a rascunhos semânticos).
- **Atualização das Skills de Mapas (`mapa_extrair_pontos_de_interesse` e `mapa_corrigir_pontos_de_interesse`)**: Substituição sistemática de `label` por `rotulo` nos exemplos e instruções, alinhando com o Princípio I (Tudo em Português) e schema v5, e instrução de preservação de `uid` pré-existente nos metadados JSON.
- **Atualização da Skill `preencher_croqui_yaml`**: Atualização do valor padrão de `ultima_migracao` para `5` e documentação de que o ciclo de auto-injeção de UIDs é resolvido executando `deploy_generated.py`.
- **Atualização dos Workflows (`processar_croqui_completo.md` e `atualizar_croqui_completo.md`)**: Inclusão de orientações claras de preservação de UIDs para os sub-agentes `ConversorMarkdown` e `ExtratorMapas` nas fases de diffing e extração.

## Capabilities

### New Capabilities

- `saneamento-uids-pipeline`: Garante o saneamento automático, contínuo e idempotente de UIDs NanoID 14c e a conversão de referências semânticas de mapa em `corrigir_database`, sem depender do número de versão de migração do croqui.

### Modified Capabilities

- `agentes-extracao-pdf`: Adiciona requisitos para que os subagentes e skills adotem `rotulo` em vez de `label`, preservem obrigatoriamente os UIDs existentes em edições e utilizem a sintaxe canônica de referências de mapas com UIDs.

## Impact

- **Código e Scripts**: `scripts/preparar_submissao_lib.py`, `scripts/finalizar_mapas.py` e testes associados em `scripts/preparar_submissao_lib_test.py`.
- **Workflows e Skills**: Arquivos `.agents/skills/*/SKILL.md` (`converter_parte_croqui_para_markdown`, `mapa_extrair_pontos_de_interesse`, `mapa_corrigir_pontos_de_interesse`, `preencher_croqui_yaml`) e `.agents/workflows/*.md` (`processar_croqui_completo`, `atualizar_croqui_completo`).
- **Compatibilidade e Modelos de IA**: Elimina o risco de alucinação de NanoIDs por LLMs ao manter o rascunho textual semântico e delegar a integridade criptográfica aos scripts determinísticos em Python.
