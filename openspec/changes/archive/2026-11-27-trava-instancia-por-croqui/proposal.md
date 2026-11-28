# Proposal

## Why

O `editor/main.py` ainda impõe uma trava global única (`ArestaEditorSingleInstanceServer`) antes mesmo de ler os argumentos de linha de comando, o que impede abrir uma segunda instância com `uv run editor/main.py <croqui>` para um croqui diferente. Embora o suporte a múltiplas janelas por croqui já exista na camada de infraestrutura (`editor/core/instancia_unica.py` e roteamento proxy em `editor/mcp/servidor.py`), a trava por croqui nunca foi conectada ao ciclo de vida do arranque e das janelas.

## What Changes

- **Substituição da trava global por trava escopada (`ArestaEditorTelaSelecao` e `ArestaEditorCroqui_<id_croqui>`)**: remoção de `NOME_SERVIDOR_PADRAO` em `editor/core/instancia_unica.py`, tornando o identificador do servidor obrigatório, adicionando helpers para trava da tela de seleção, encerramento seguro de servidor local, extração determinística de `id_croqui` de uma pasta de croqui e isolamento por variável de ambiente `ARESTA_PREFIXO_IPC` para testes.
- **Resolução antecipada do croqui na inicialização (`editor/main.py`)**: validação e extração do `id_croqui` dos argumentos da linha de comando antes da checagem de instância única; abertura simultânea para croquis distintos, elevação da janela correspondente apenas quando o mesmo `id_croqui` já estiver aberto, e uso da trava `ArestaEditorTelaSelecao` apenas enquanto a `TelaDeCarregamento` estiver aguardando seleção no modo padrão.
- **Ciclo de vida da trava por croqui na `JanelaPrincipal` e guarda na `TelaDeCarregamento`**: cada `JanelaPrincipal` adquire `ArestaEditorCroqui_<id_croqui>` ao carregar o croqui (elevando especificamente a si mesma ao receber `PING`), atualiza a trava caso o `id` mude ao salvar e libera a trava ao fechar; a `TelaDeCarregamento` bloqueia e foca a janela existente caso o usuário tente abrir, importar ou criar um croqui já aberto em outro processo.
- **Serialização e proteção de concorrência entre múltiplos processos**:
  - `editor/mcp/sessao.py`: gravação e atualização atômicas sob lock em `mcp_sessoes.json` e `mcp_sessao.json`, preservando a sessão primária ativa em `mcp_sessao.json` quando processos secundários são iniciados.
  - `editor/core/sync.py`: proteção das operações Git compartilhadas sobre `aresta_db` com `trava_arquivo_operacao` em lockfile externo ao repositório.
  - `editor/core/workspace.py`: serialização da renomeação Git, compilação em `generated/` e atualização de `STATUS_CROQUIS.md` em `LocalRepoWorkspace` via `trava_arquivo_operacao` no diretório de dados do aplicativo.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-inicializacao`: substituição da trava global de instância única no arranque por trava escopada por tela de seleção e por croqui, permitindo múltiplos processos paralelos em croquis distintos.
- `editor-local-mode`: suporte a múltiplas janelas/processos simultâneos em modo local sobre croquis diferentes, com serialização de escrita na pasta compartilhada `generated/` e em `STATUS_CROQUIS.md`.
- `editor-tela-de-carregamento`: verificação de croqui já aberto em outra instância ao abrir do histórico, importar oficial ou criar novo croqui, elevando a janela existente sem duplicar janelas.
- `editor-controle-mcp`: preservação atômica da sessão primária ativa em `mcp_sessao.json` quando múltiplas instâncias sobem em paralelo na porta `27379+`.

## Impact

- Código de produção: `editor/core/instancia_unica.py`, `editor/mcp/sessao.py`, `editor/core/sync.py`, `editor/core/workspace.py`, `editor/legacy_views/tela_de_carregamento.py`, `editor/legacy_views/area_principal.py`, `editor/main.py`.
- Suítes de teste (TDD sem mocks internos, 100% de cobertura nos módulos alvo): `editor/core/instancia_unica_test.py`, `editor/mcp/sessao_test.py`, `editor/core/sync_test.py`, `editor/core/workspace_test.py`, `editor/legacy_views/tela_de_carregamento_test.py`, `editor/legacy_views/area_principal_test.py`, `editor/main_test.py`.
- Especificações OpenSpec: `openspec/specs/editor-inicializacao/spec.md`, `openspec/specs/editor-local-mode/spec.md`, `openspec/specs/editor-tela-de-carregamento/spec.md`, `openspec/specs/editor-controle-mcp/spec.md`.
