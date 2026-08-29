# Proposta: Onda 2 - Tipagem Estática do Núcleo de Dados, Modelos e Core

## Why

Os módulos fundamentais do editor localizados em `editor/core/` gerenciam o ciclo de vida dos dados (armazenamento, coordenadas, workspace, sessões de usuário, histórico de comandos, diário de recuperação e telemetria). Erros de tipagem nesses módulos de base se propagam diretamente para controllers e views, causando instabilidade e crashes no aplicativo. A Onda 2 converte todo o núcleo de base em código estaticamente tipado e estrito, garantindo segurança de contratos e `None-safety` nas camadas centrais.

## What Changes

- Tipagem estática estrita (`mypy --strict`) em todos os módulos centrais de `editor/core/`:
  - `storage.py`, `contexto.py`, `coordenadas.py`, `workspace.py`
  - `gerenciador_sessao.py`, `cliente_auth_supabase.py`, `servico_submissao.py`, `servico_loja.py`
  - `telemetria.py`, `historico.py`, `diario.py`, `registro_log.py`
  - `croqui_experimental.py`, `croqui_format.py`, `formatacao.py`, `geometrias_poi.py`, `imagens_markdown.py`, `processamento_imagem_campo.py`, `proto_comments.py`, `sync.py`, `version.py`, `worker.py`, `workflow_export_import.py`
- Correção de potenciais retornos `None` não tipados, parâmetros ambíguos e substituição de `Any` por tipos estritos ou uniões explícitas (`T | None`).
- Inclusão dos módulos de `editor/core/` na validação contínua do teste guardião `tests/tipagem_estatica_test.py`.
- Garantia de 100% de cobertura de testes unitários para todas as refatorações de tipagem.

## Capabilities

### New Capabilities
- `tipagem-estatica-editor-core`: Tipagem estática estrita e certificação de zero erros MyPy em todos os arquivos de lógica base e gerenciamento de estado em `editor/core/`.

### Modified Capabilities
<!-- Nenhuma especificação funcional teve seus requisitos de comportamento de negócio alterados -->

## Impact

- `editor/core/*.py`: Todos os arquivos passam a ter anotações completas de parâmetros, variáveis e retornos.
- `tests/tipagem_estatica_test.py`: Expandido para incluir a checagem de conformidade de `editor/core/` no MyPy e no analisador de AST.
