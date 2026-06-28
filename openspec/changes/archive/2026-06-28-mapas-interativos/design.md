## Context

Os mapas gerais (índices de croquis) são imagens puramente ilustrativas referenciadas como textos secundários, causando inconsistência com os mapas interativos de setores.

## Goals / Non-Goals

**Goals:**
- Prover suporte completo a mapas interativos em nível de `Pico`.
- Manter a compatibilidade com a infraestrutura existente de scripts e agentes, evitando refatorações drásticas.
- Migrar automaticamente os dados legados de mapas gerais.
- Garantir 100% de test coverage e conformidade total com `PRINCIPIOS.md` (TDD, Library-First, e regras de Protobuf).

**Non-Goals:**
- Implementar UI de referência de Setor/Grupo diretamente no painel do Editor de Mapas (será deixado para melhoria futura).
- Alterar o pipeline do app frontend (ele já suporta as referências).

## Decisions

- **TDD e Cobertura 100%**:
  Todas as modificações nos scripts (`preparar_extracao_de_mapas.py`, `finalizar_mapas.py`) e componentes do editor serão precedidas por testes falhos (Red-Green-Refactor). Para a migração, a lógica central será isolada (Library-First) em funções puras para facilitar os testes de unidade, antes de ser injetada no runner de migração.

- **Design de Protobuf (Encapsulamento)**:
  Em conformidade com `PRINCIPIOS.md`, o wrapper de mapas externos utilizará o padrão de `oneof` encapsulado (`ArquivoMapas`), possuindo o `(aresta.mensagem_formato_na_ui) = ONEOF_CONTEUDO` na mensagem externa para perfeita integração com o editor.

- **Usar um ArquivoMapas externo (.md) apenas com frontmatter**:
  Em vez de adicionar os mapas brutos dentro do YAML principal do croqui (`croqui.yaml`), criaremos a abstração `ArquivoMapas` no Protobuf que aponta para um arquivo Markdown contendo os mapas dentro do seu frontmatter.
  - *Rationale*: Isso permite que os scripts de extração Python funcionem com `mapas_gerais.md` exatamente como fazem para `setor_*.md`, sem necessidade de refatorar seu mecanismo de _parsing_.

- **Manter o nome `mapas_gerais.md`**:
  O arquivo continuará com o mesmo nome na base.
  - *Rationale*: Facilita o script de migração e a rotulagem legada no pipeline do PDF. O arquivo perderá seu conteúdo de texto, mantendo apenas o frontmatter.

## Risks / Trade-offs

- [Risk] Os agentes de IA na Fase 2 podem ficar confusos ao gerar um arquivo MD sem texto, preenchendo apenas o frontmatter.
  → Mitigação: Instruções explícitas (via skill update) garantirão que a geração do frontmatter `mapas:` será priorizada.
- [Risk] Migração corrompendo arquivos `croqui.yaml`.
  → Mitigação: 100% test coverage da rotina de migração em cenários simulados (testes de integração em primeiro lugar) garantirá que nenhum YAML de produção será danificado.
