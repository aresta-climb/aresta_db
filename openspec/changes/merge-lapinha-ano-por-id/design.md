## Context

O croqui da Gruta da Lapinha está consolidado no banco de dados da Aresta (na pasta `br_mg_lagoa_santa_gruta_da_lapinha`), mas 103 vias estão sem o campo `data_abertura` (ano de conquista). Um arquivo CSV de levantamento das vias (`Vias da Lapinha.xlsx - Plan1.csv`) contém esse dado, além de informações redundantes que podem servir de validação.

## Goals / Non-Goals

**Goals:**
- Criar um script para mesclar o campo `ano` do CSV no campo `data_abertura` dos arquivos YAML (`setor_mapa_*.md`).
- Utilizar os IDs (chave `N°` no CSV e chave `ids` no YAML) para realizar o mapeamento seguro, evitando problemas de variação de string (nome).
- Usar o nome do YAML caso haja divergência (e.g. "Ben moon" vs "Bem moon").

**Non-Goals:**
- Não iremos alterar os nomes das vias no Croqui atual para refletir o CSV caso sejam diferentes, pois o YAML já passou por uma padronização manual que está mais confiável.
- Não iremos realizar a migração de outros campos do CSV neste momento, mantendo o escopo estrito na `data_abertura`.

## Decisions

- **Estratégia de Parsing**: Python com biblioteca nativa de manipulação de strings/regex para o Frontmatter YAML, ou usar `pyyaml` tendo o cuidado de não sobrescrever formatações customizadas de Markdown que ficam abaixo do frontmatter.
- **Merge Seguro (ID-based)**: Como a exploração inicial confirmou que a ordem e as chaves batem em exatos 128 registros, o merge será por ID numérico.

## Risks / Trade-offs

- **[Risk]** Quebrar o arquivo Markdown ou perder comentários YAML. → **Mitigation**: Usaremos regex cuidadoso ou um parsing seguro (separando o yaml header do markdown body) e salvaremos com a mesma estrutura original.
