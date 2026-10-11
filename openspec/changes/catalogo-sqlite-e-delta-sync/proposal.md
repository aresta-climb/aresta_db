# Proposal: Catálogo SQLite e Sincronização de Deltas

## Why

Atualmente, o aplicativo móvel do Aresta depende exclusivamente do carregamento completo do `indice.binarypb` e do download de croquis individuais para busca de vias e setores. Além disso, a futura resolução de links curtos e QR Codes (no formato `https://aresta.cc/<uid>`) exige uma forma rápida, de baixa latência e eficiente para recuperar os dados de uma via, setor ou croqui sem exigir o carregamento ou decodificação do Protobuf em workers de borda (Cloudflare Workers/D1), nem forçar o download completo de megabytes de dados pelo aplicativo apenas para uma busca textual.

Esta mudança introduz a geração automatizada de um catálogo SQLite leve (`catalogo.db` e `catalogo.db.gz`) durante o processo de deploy (`deploy_generated.py`), composto por duas tabelas normalizadas (`catalogo_croquis` e `catalogo_aresta`), além de mecanismos de diff SQL para alimentar uma tabela de deltas versionados no Cloudflare D1. Isso viabiliza busca global textual instantânea offline no app e resolução em milissegundos de links sociais e QR Codes na borda com OpenGraph completo.

## What Changes

- **Biblioteca de geração do catálogo SQLite (`scripts/gerar_catalogo_sqlite_lib.py`)**:
  - Extrai metadados dos croquis (`croqui_uid`, `id_slug`, `nome`, `cidade`, `uf`) para a tabela `catalogo_croquis`.
  - Extrai dados de todas as escaladas (`uid`, `croqui_uid`, `nome`, `grau`, `tipo`, `setor_nome`, `setor_uid`) para a tabela `catalogo_aresta`.
  - Índices otimizados para busca textual rápida (`LIKE` / prefixos) e consultas por `uid` e `croqui_uid`.
  - Suporte a geração total (todos os croquis) e atualização parcial/incremental (`DELETE WHERE croqui_uid IN (...)` + `INSERT`) preservando o restante do banco em execuções com alvos específicos (`--target`).
- **Passo E no script de deploy (`scripts/deploy_generated.py`)**:
  - Execução automatizada ao final da compilação de croquis para gerar `generated/catalogo.db` e sua versão comprimida `generated/catalogo.db.gz`.
  - Inclusão dos artefatos do catálogo no manifesto de serving (`arquivos_serving.yaml`).
- **Geração e extração de deltas SQL para Cloudflare D1 (`scripts/gerar_deltas_catalogo.py`)**:
  - Mecanismo que compara duas versões do `catalogo.db` (versão anterior vs. nova versão gerada) usando comandos `EXCEPT` do SQLite.
  - Produz changeset em formato estruturado (inserções/atualizações e deleções) para alimentar a tabela `deltas_catalogo` no Cloudflare D1.
- **Suporte arquitetural a links e metadados OpenGraph (`aresta.cc/<uid>`)**:
  - Especificação do contrato com o Cloudflare Worker para renderização de Landing Page ultra-leve com OpenGraph e Twitter Cards enriquecidos via `JOIN` entre `catalogo_aresta` e `catalogo_croquis`.

## Capabilities

### New Capabilities

- `catalogo-sqlite-delta-sync`: Geração e sincronização do banco de dados SQLite leve (`catalogo.db`), mantendo tabelas `catalogo_croquis` e `catalogo_aresta`, índices de busca, suporte a atualizações parciais durante o deploy e extração de deltas versionados para o Cloudflare D1 e resolução de links `aresta.cc/<uid>`.

### Modified Capabilities

*(Nenhuma capacidade existente sofre alteração de requisitos de sistema; este recurso expande o pipeline sem modificar os contratos dos formatos existentes de `compilado.binarypb` ou `indice.binarypb`)*.

## Impact

- **Pipeline de deploy (`deploy_generated.py`)**: Novo passo que produz `generated/catalogo.db` e `generated/catalogo.db.gz`.
- **Manifesto de serving (`arquivos_serving.yaml`)**: Ganha o registro dos novos arquivos de catálogo e seus respectivos hashes SHA-256.
- **Armazenamento e Rede**: O catálogo completo comprimido adiciona aproximadamente ~200 a 300 KB ao pacote de dados globais servidos pelo CDN.
- **Novas ferramentas**: `scripts/gerar_catalogo_sqlite_lib.py`, `scripts/gerar_catalogo_sqlite_lib_test.py`, `scripts/gerar_deltas_catalogo.py` e `scripts/gerar_deltas_catalogo_test.py`.
- **Repositório irmão (`aresta_app`)**: O app móvel poderá consumir `catalogo.db` como asset local pré-embarcado e sincronizar deltas incrementais via Cloudflare Worker.
