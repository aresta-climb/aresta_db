## Why

Atualmente, apenas os mapas de setores são interativos. Os mapas gerais (e os mapas de grupos) são renderizados apenas como imagens estáticas ou com listas em Markdown (`mapas_gerais.md`). Isso causa uma inconsistência na experiência do usuário e dificulta a descoberta visual de blocos e setores no aplicativo. Queremos migrar totalmente o esquema para que *todos* os mapas mostrados no app sejam interativos, reaproveitando o sistema atual de POIs (Pontos de Interesse) e Referências.

A implementação seguirá estritamente o `PRINCIPIOS.md`, adotando a abordagem TDD (Test-Driven Development) com garantia de 100% de cobertura de testes de unidade e integração para todas as alterações.

## What Changes

- Criação da abstração `ArquivoMapas` no `croqui.proto` para permitir coleções de mapas armazenadas como YAML Frontmatter em arquivos Markdown externos (seguindo as regras de encapsulamento de `oneof`).
- Inclusão do campo `mapas_gerais` na mensagem `Pico`.
- Criação de bibliotecas (Library-First) totalmente testadas para a migração de banco de dados (`0003_migrar_mapas_gerais.py`) que converte os antigos `mapas_gerais.md` em arquivos estruturais apenas com YAML.
- Atualização orientada a testes dos scripts de extração (`preparar_extracao_de_mapas.py` e `finalizar_mapas.py`) para lerem o frontmatter do novo `mapas_gerais.md`.
- Atualização das instruções dos agentes de IA (`separar_croqui_pdf_em_partes` e `converter_parte_croqui_para_markdown`) para extraírem índices geográficos no novo formato.
- Inclusão do nó de "Mapas Gerais" na árvore de navegação do Editor de Croquis, com testes E2E/integração garantindo a UI.

## Capabilities

### New Capabilities
- `mapas-gerais-interativos`: Suporte a mapas em nível de Pico com arquivos auxiliares baseados em YAML Frontmatter.

### Modified Capabilities
- `agentes-extracao-pdf`: Regras de como os sub-agentes geram os arquivos MD da parte de mapas gerais.

## Impact

- `aresta_api/proto/croqui.proto`
- `migracoes/0003_migrar_mapas_gerais.py`
- `scripts/preparar_extracao_de_mapas.py` e `scripts/finalizar_mapas.py`
- `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md`
- `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`
- UI do Editor de Croquis
