# Proposal

## Why

Ao salvar um croqui pelo Editor Aresta (tanto no modo repositório local quanto no modo experimental que gera Pull Requests), vários arquivos que não foram editados pelo usuário aparecem como modificados no Git (`git status` e commits de PR). Isso ocorre por quatro problemas combinados:
1. `CroquiModel.extrair_arquivos_e_serializar` reescreve incondicionalmente todos os arquivos `.md` do croqui a cada salvamento, alterando `mtime` e convertendo arquivos legados com `CRLF` no working tree para `LF` (deixando o tamanho `size` defasado no `.git/index`), enquanto outros pontos (`TarefaSalvamento.run`, `salvar_md_com_frontmatter`, `preparar_submissao_lib.py` e `medir_saude_croquis.py`) gravam arquivos sem `newline="\n"`, introduzindo `CRLF` no Windows.
2. `editor/models/croqui_model.py` registra um `_str_representer` global no `yaml.Dumper` que não formata strings multilinhas com `|` (`|-`), sobrescrevendo o representer de `scripts/preparar_submissao_lib.py` e corrompendo a formatação de descrições multilinhas em arquivos `.md`, `compilado.yaml` e `indice.yaml`.
3. Os repositórios Git gerenciados via `pygit2` (`GerenciadorSincronizacao` e `GerenciadorCroquiExperimental`) não forçam `core.autocrlf = False`, e `ServicoSubmissao` usa comparação binária estrita (`filecmp.cmp`), listando arquivos em PRs quando há apenas diferença residual de `CRLF` vs `LF`.
4. `scripts/medir_saude_croquis.py` sobrescreve `STATUS_CROQUIS.md` a cada salvamento atualizando apenas o cabeçalho `Relatório gerado em:`, mesmo quando nenhuma métrica da tabela mudou.

## What Changes

- **Unificação da serialização YAML e escrita condicional em LF (`\n`)**:
  - Centralizar a configuração do dumper/representer YAML (suportando blocos literais `|` para strings com `\n` e aspas simples `'` para strings puramente numéricas positivas ou negativas) para que `editor/models/croqui_model.py`, `editor/core/worker.py`, `editor/core/croqui_experimental.py`, `scripts/markdown_frontmatter_lib.py`, `scripts/preparar_submissao_lib.py` e `scripts/deploy_generated.py` produzam exatamente a mesma formatação YAML sem conflito de estado global.
  - Criar função utilitária de escrita textual idempotente que sempre utiliza quebras de linha `LF` (`\n`) e **só grava no disco quando o conteúdo normalizado realmente mudou**, evitando tocar em arquivos `.md` e `.yaml` não editados.
- **Proteção de `LF` nos repositórios `pygit2` e no fluxo de Pull Request**:
  - Configurar explicitamente `core.autocrlf = False` ao inicializar e fazer checkout nos repositórios `pygit2` (`GerenciadorSincronizacao` e `GerenciadorCroquiExperimental`).
  - Tornar a detecção e o espelhamento de arquivos modificados em `ServicoSubmissao` (`obter_arquivos_modificados` e `_espelhar_diretorio`) imunes a diferenças puras de `CRLF` vs `LF` em arquivos textuais (`.md`, `.yaml`, `.json`).
- **Atualização condicional do `STATUS_CROQUIS.md`**:
  - Alterar `scripts/medir_saude_croquis.py` para comparar a tabela gerada com a tabela existente em `STATUS_CROQUIS.md` e só regravar o arquivo (atualizando o timestamp `Relatório gerado em:` com quebras `LF`) quando houver mudança real nos dados da tabela.
- **Renormalização do índice e arquivos pendentes**:
  - Renormalizar quebras de linha no repositório e limpar as modificações espúrias pendentes na Gruta da Lapinha (`database/br_mg_lagoa_santa_gruta_da_lapinha/` e `generated/`).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada; os requisitos estendem capabilities existentes. -->

### Modified Capabilities
- `editor-serializacao-croqui`: Adiciona requisitos de unificação do representer YAML (blocos `|` para multilinhas e aspas `'` para dígitos), escrita condicional apenas quando o conteúdo mudar com quebras de linha estritas em `LF` (`\n`), e atualização condicional de `STATUS_CROQUIS.md`.
- `editor-sincronizacao-git`: Adiciona requisito para forçar `core.autocrlf = False` nas operações de inicialização, clone e checkout com `pygit2`.
- `editor-submissao-sugestoes`: Adiciona requisito para ignorar diferenças exclusivas de `CRLF` vs `LF` na detecção e espelhamento de arquivos textuais modificados para Pull Requests.

## Impact

- `editor/core/serializacao_util.py` e `scripts/markdown_frontmatter_lib.py`
- `editor/models/croqui_model.py` e `editor/core/worker.py`
- `editor/core/sync.py`, `editor/core/croqui_experimental.py` e `editor/core/servico_submissao.py`
- `scripts/preparar_submissao_lib.py`, `scripts/deploy_generated.py` e `scripts/medir_saude_croquis.py`
- Índices e arquivos da base de dados (`database/br_mg_lagoa_santa_gruta_da_lapinha/`, `generated/`, `STATUS_CROQUIS.md`)
