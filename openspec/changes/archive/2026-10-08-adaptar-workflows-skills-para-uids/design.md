# Design: Saneamento Contínuo de UIDs e Modernização de Skills/Workflows

## Context

O repositório Aresta Climb adotou o modelo **Pure NanoID 14c Universal** e a renomeação de `label` para `rotulo` na versão 5 do schema (vide `proposal.md` e a change `introduzir-ids-estaveis-croqui`).
Contudo, o pipeline de ingestão e compilação dependia exclusivamente do `migrador.py`, que avalia se a versão numérica gravada em `croqui.yaml` (`ultima_migracao`) é menor que o ID do script de migração.
Quando um croqui novo é criado contendo `ultima_migracao: 5`, o motor de migrações não executa a injeção de UIDs, e qualquer rascunho textual gerado por agentes LLM sem UIDs falha na validação de `auditar_uids_database`. Além disso, as skills instruíam o formato legado com `label`, `escalada:` e `ids:`.

## Goals / Non-Goals

**Goals:**
- Prover uma rotina contínua, idempotente e segura de saneamento de UIDs (`sanear_uids_database`) integrada diretamente ao ciclo de `corrigir_database` em `scripts/preparar_submissao_lib.py`.
- Atualizar `scripts/finalizar_mapas.py` para gerar UIDs e utilizar a chave `rotulo` ao transferir pontos de interesse do JSON para os arquivos Markdown.
- Atualizar todas as 4 skills de processamento (`converter_parte_croqui_para_markdown`, `mapa_extrair_pontos_de_interesse`, `mapa_corrigir_pontos_de_interesse`, `preencher_croqui_yaml`) para adotar a nova terminologia (`rotulo`), instruir preservação de UIDs e definir a sintaxe canônica de referências.
- Atualizar os workflows (`processar_croqui_completo.md` e `atualizar_croqui_completo.md`) com diretrizes de preservação de UIDs para os sub-agentes de diffing.

**Non-Goals:**
- Não exigir que modelos de linguagem (LLMs) gerem strings NanoID 14c manualmente em prompts textuais.
- Não alterar definições de Protobuf nem criar novas migrações lineares (mantém migração 5).

## Decisions

### 1. Saneamento Automatizado por Scripts vs Geração Manual por LLMs
- **Decisão:** Manter os rascunhos de LLMs semânticos (nomes de vias e setores, rótulos numéricos como `"01"`) e executar a injeção determinística de UIDs via scripts Python.
- **Alternativa considerada:** Exigir que a LLM preenchesse `uid: <nanoid_14c>` no YAML de cada setor e via.
- **Justificativa:** LLMs frequentemente geram comprimentos incorretos (13 ou 15 caracteres), usam caracteres fora de Base62 ou sofrem alucinação ao sincronizar relacionamentos cruzados entre arquivos diferentes. A automação em Python garante integridade criptográfica instantânea e custo zero de contexto.

### 2. Integração do Saneamento Idempotente em `corrigir_database`
- **Decisão:** Chamar a rotina idempotente de atribuição de UIDs e resolução de referências diretamente dentro de `corrigir_database(pico_path)` em `scripts/preparar_submissao_lib.py`, logo após `aplicar_migracoes(pico_path)`.
- **Alternativa considerada:** Criar um comando CLI separado que precisaria ser chamado manualmente pelos agentes antes de cada deploy.
- **Justificativa:** Integrar a rotina em `corrigir_database` faz com que qualquer comando de compilação padrão (`deploy_generated.py`) saneie e converta automaticamente os arquivos antes da validação estrita de `auditar_uids_database`, tornando o fluxo à prova de falhas.

### 3. Preservação Estrita de UIDs em Atualizações e Diffing
- **Decisão:** Instruir explicitamente nos prompts de subagentes e na skill de markdown que UIDs existentes (`uid`, `alvo_uid`, `pontos_uids`) são sagrados e nunca devem ser alterados ou apagados.
- **Justificativa:** Vias e setores já mapeados possuem placas físicas gravadas com QR Code (`https://aresta.cc/<uid>`) e links compartilhados. Mutações arbitrárias de UIDs durante re-conversões quebrariam a permanência do identificador.

## Risks / Trade-offs

- **[Risco: Ambiguidade em nomes idênticos de escaladas no mesmo croqui]** → **Mitigação:** A resolução de referências semânticas em `sanear_uids_database` cataloga primeiro pelo par `(setor, escalada)` e avisa em caso de duplicatas simples, priorizando vínculos contextuais.
- **[Risco: Alteração acidental de formatação ou comentários em arquivos Markdown]** → **Mitigação:** Utilização da biblioteca `ruamel.yaml` com preservação estrita de comentários e aspas, herdada da migração 5.
