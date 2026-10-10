# Proposal

## Why

Atualmente, centenas de arquivos Markdown de setores e grupos contêm cabeçalhos H1 (`# Setor <Nome>`) no corpo da descrição. No aplicativo móvel e na web, o nome do setor/grupo já é renderizado nativamente pela interface gráfica como o título principal da tela. Quando o corpo Markdown também inclui um H1, ocorre duplicação visual desagradável no app. Em aproximadamente 200 arquivos, o Markdown continha exclusivamente o título e nenhum outro texto descritivo.

Adicionalmente, os nomes dos setores no YAML Frontmatter estavam heterogêneos: parte continha o prefixo "Setor ", parte continha "Bloco ", e mais de 200 setores não tinham nenhum prefixo.

Padronizar os nomes de setores com o prefixo "Setor " (mantendo "Bloco " para blocos de boulder), remover os títulos H1 redundantes do corpo Markdown e introduzir um aviso de integridade no deploy garante consistência visual imediata e previne regressões futuras.

## What Changes

- **Migração do Banco de Dados (One-off / Utilitário de Saneamento)**:
  - Remove linhas de cabeçalho H1 (`# `) do corpo do Markdown de setores e grupos.
  - Se o corpo do Markdown continha unicamente o H1, o corpo é esvaziado, eliminando descrições inúteis.
  - Se um arquivo estiver sem o campo `nome:` no frontmatter (ex: `setor_bigorna_ou_lapa_da_zumba.md`), o nome é recuperado a partir do H1 antes de sua remoção.
  - Padroniza o campo `nome:` no frontmatter de setores: se não começar com "Setor " nem com "Bloco ", adiciona o prefixo "Setor ".
  - Mantém nomes que começam com "Bloco " inalterados (sem prefixar com "Setor Bloco").
  - Mantém grupos (`grupo_*.md`) sem inserção compulsória de prefixo "Grupo ".
- **Aviso de Integridade no `deploy_generated.py`**:
  - Nova checagem `verificar_titulos_em_descricao_setor_grupo` executada no Passo A da compilação.
  - Emite aviso claro caso a descrição de qualquer setor ou grupo contenha linhas de cabeçalho H1 (`# `).
- **Atualização da Skill `converter_parte_croqui_para_markdown`**:
  - Adiciona orientação estrita nas seções de Setor e Grupo proibindo a inclusão de títulos H1 no corpo do Markdown e instruindo a utilização correta do campo `nome` no frontmatter com o prefixo apropriado.

## Capabilities

### New Capabilities
- `validacao-titulos-markdown-deploy`: Define a validação no deploy contra cabeçalhos H1 em descrições de setores e grupos, bem como as diretrizes de padronização do campo `nome` no frontmatter.

### Modified Capabilities
<!-- Nenhuma capability existente tem seus requisitos alterados. -->

## Impact

- **Banco de Dados**: Arquivos `database/**/*.md` (setores e grupos) com cabeçalhos H1 removidos e `nome:` padronizado.
- **Pipeline de Deploy**: `scripts/deploy_generated.py` e testes associados em `scripts/deploy_generated_test.py`.
- **Agentes e Documentação**: Skill `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`.
