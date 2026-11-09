# Proposal

## Why

Agentes autônomos e curadores que utilizam o servidor MCP do Editor Aresta (`editor-aresta`) para revisar croquis extensos — como a revisão completa da Gruta da Lapinha a partir da 2ª edição do livro *"O Melhor do Calcário – Escaladas de Minas"* — enfrentam duas limitações operacionais: (1) não existe uma ferramenta atômica (`aresta_migrar_escalada`) para mover uma `Escalada` de um `Setor` para outro preservando seu `uid` e vínculos de mapas em um único `CmdMacro`, e (2) `aresta_alterar_campo` opera em apenas um `alvo` por chamada, exigindo dezenas de chamadas JSON-RPC sequenciais e gerando dezenas de entradas fragmentadas na pilha de histórico (`QUndoStack`) ao atualizar graduações, datas, conquistadores e nomes em lote.

## What Changes

- **Nova ferramenta MCP `aresta_migrar_escalada` e método `CroquiController.migrar_escalada`**:
  - Migra atomicamente uma `Escalada` de um `Setor` de origem para um `Setor` de destino via `CmdMacro` (`CmdRemoverRepeated` + `CmdAdicionarRepeated`), preservando integralmente seu `uid` NanoID, submensagens (`enfiadas`, `reunioes`), imagens em memória RAM e referências em mapas (`Mapa.Referencia`), com resolução automática do setor e índice de origem a partir do `alvo_escalada` (UID ou caminho).
- **Nova ferramenta MCP `aresta_alterar_em_lote` e método `CroquiController.alterar_em_lote`**:
  - Recebe uma lista `operacoes` contendo múltiplos alvos (`alvo` + `campo`/`valor` ou `campos`) e aplica todas as alterações (primitivos, enums por nome, submensagens, variantes `oneof` e substituições de listas `repeated`) agrupadas em um único `CmdMacro` atômico na `QUndoStack`, com validação *fail-fast* integral antes de empilhar qualquer comando no histórico.
- **Execução 100% via MCP da revisão do croqui `br_mg_lagoa_santa_gruta_da_lapinha`**:
  - Atualização completa do croqui da Gruta da Lapinha através do servidor MCP do Editor Aresta (servindo também como teste de estresse real das novas ferramentas), alinhando topologia de POIs/referências (`44`/`45`, `50`/`51`, `61`/`62`/`63`, `92`/`93` e nova via `132` *Meio Cubanos* migrada do Setor 8 para o Setor 6, mais POI `122`), tipo de proteção (`60`), datas de abertura (`08`, `09`, `61`, `90`), nomes de vias (`06`, `08`, `13`, `32`, `58`, `61`, `62`, `108`, `127`, `129`), 22 graduações segundo o livro (com mapeamento `< 7º`: `'b'` -> `_BARRA_` e `'c'` -> `SUP`), padronização de conquistadores no formato `<Nome Completo> "<Apelido>"` (incluindo `Fábio Luiz Faria "Fabinho"` e co-conquistadores do PDF Rumos) e textos/descrições (`mapas_gerais.md` e vias `124`/`125`), preservando integralmente os dados técnicos de inspeção da GTEL (2022/2026).

## Capabilities

### New Capabilities

<!-- Nenhuma nova capability isolada; estendemos as capabilities canônicas existentes do editor. -->

### Modified Capabilities

- `editor-controle-mcp`: Adiciona as ferramentas `aresta_migrar_escalada` e `aresta_alterar_em_lote` ao catálogo MCP do Editor Aresta, permitindo migração entre setores por UID e mutação multi-alvo atômica em lote.
- `undo-redo-protobuf`: Estende as operações compostas de alto nível via `CmdMacro` no `CroquiController` com `migrar_escalada` (preservando `uid` e imagens em RAM) e `alterar_em_lote` (validação *fail-fast* multi-alvo em um único `CmdMacro`).

## Impact

- **Código Afetado**:
  - `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py` (novos métodos `migrar_escalada` e `alterar_em_lote`).
  - `editor/mcp/ferramentas_comandos.py` e `editor/mcp/ferramentas_comandos_test.py` (registro e validação das ferramentas `aresta_migrar_escalada` e `aresta_alterar_em_lote`).
  - `editor/controllers/README.md` (documentação atualizada dos novos métodos de controlador).
- **Dados Afetados (na fase de aplicação via MCP)**:
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/` (`croqui.yaml`, `mapas_gerais.md`, `setor_mapa_1.md` a `setor_mapa_10.md`).
