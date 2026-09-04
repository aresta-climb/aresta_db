## Context

O Editor Aresta mantém o arquivo `editor/core/version.py` continuamente no formato `X.Y.Z-dev` durante o ciclo de desenvolvimento normal (por exemplo, `0.2.1-dev`), atualizado automaticamente pelo script `calculate_next_dev.py` após cada release.

Quando um release é acionado, queremos que a seleção do tipo de incremento (`patch`, `minor`, `major` ou `custom`) defina imediatamente a versão canônica oficial do binário e das tags.

## Goals / Non-Goals

**Goals:**
- Implementar biblioteca puramente funcional `calculate_release_version.py` em `editor/release_tools/` com interface CLI compatível com scripts e GitHub Actions.
- Implementar suite de testes exaustiva com 100% de cobertura de código (branches, statements e erros).
- Suportar incremento de versões tanto com sufixo `-dev` (padrão do repo) quanto versões sem sufixo.
- Atualizar `.github/workflows/release-editor.yml` para utilizar inputs tipados (`type: choice` e `type: string`) e integrar a chamada da ferramenta logo após o checkout.

**Non-Goals:**
- Não alterar a lógica pós-release de `calculate_next_dev.py` (que já soma +1 no patch e coloca `-dev`).
- Não remover a possibilidade de versões personalizadas arbitrárias (garantida pela opção `custom`).

## Decisions

### 1. Regras de Transição SemVer a partir do Estado `-dev`
Como a versão em desenvolvimento já foi pré-incrementada com `patch + 1` no término do release anterior (ex: `0.2.1-dev` após o release `0.2.0`):
- **`patch`**: Remove o sufixo `-dev`. Exemplo: `0.2.1-dev` -> `0.2.1`.
- **`minor`**: Incrementa o `minor` e redefine `patch = 0`. Exemplo: `0.2.1-dev` -> `0.3.0`.
- **`major`**: Incrementa o `major` e redefine `minor = 0, patch = 0`. Exemplo: `0.2.1-dev` -> `1.0.0`.
- **`custom`**: Valida a versão fornecida via regex SemVer e garante que seja estritamente superior à versão atual base.

Se a versão de entrada não possuir `-dev` (ex: `0.2.0`):
- `patch`: `0.2.0` -> `0.2.1`
- `minor`: `0.2.0` -> `0.3.0`
- `major`: `0.2.0` -> `1.0.0`

### 2. Leitura da Versão Atual
A ferramenta permitirá tanto receber a versão explicitamente via `--versao-atual` ou ler diretamente de um arquivo fornecido (`--arquivo`, default: `editor/core/version.py`), facilitando seu uso no CI ou em scripts locais.

## Risks / Trade-offs

- **[Risco] Esquecer de fornecer custom version quando bump_type=custom**:
  - *Mitigação*: A ferramenta valida que `--custom` não pode estar vazio se `--tipo custom` for selecionado, emitindo mensagem de erro clara em stderr e código de saída 1.
