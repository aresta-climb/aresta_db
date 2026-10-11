# Design

## Context

Atualmente, `scripts/migrador.py` determina o caminho dos scripts de migração por um caminho relativo fixo (`Path(__file__).resolve().parent.parent / "migracoes"`). No entanto:
1. Em ambientes congelados pelo PyInstaller (`sys.frozen = True`), os arquivos não residem na estrutura de diretórios do repositório, e `editor/EditorAresta.spec` não declarava a pasta `migracoes/` em `datas`.
2. O aplicativo possui um clone raso sincronizado do repositório oficial em `GerenciadorCaminhos().obter_caminho_base_repo()`, mas `migrador.py` não o consultava como fallback.
3. Se `obter_ultima_versao_migracao()` não encontra a pasta, ela retorna `0`, fazendo com que novos croquis experimentais e arquivos persistidos sejam gravados com `ultima_migracao: 0`.
4. O validador do CI (`serving/pr_db_validator.py`) não checava se `ultima_migracao` era igual à versão atual do repositório, e o workflow `pr-db-validator.yml` não incluía `migracoes` em seu `sparse-checkout`.

## Goals / Non-Goals

**Goals:**
- Garantir que `obter_caminho_migracoes()` e `obter_ultima_versao_migracao()` sempre localizem a pasta de migrações, seja em desenvolvimento, no bundle PyInstaller ou no repositório base local.
- Incluir `migracoes/` nos `datas` de `editor/EditorAresta.spec`.
- Garantir que croquis criados, importados, salvos e processados por `corrigir_database` gravem a versão máxima da migração em `croqui.yaml`.
- Validar no CI (`serving/pr_db_validator.py`) que todo croqui em `database/` submetido em PRs possui `ultima_migracao == obter_ultima_versao_migracao()`.
- Atualizar o `sparse-checkout` de `.github/workflows/pr-db-validator.yml` para baixar a pasta `migracoes`.

**Non-Goals:**
- Não alterar a implementação ou o escopo das migrações já existentes (`0001` a `0005`).
- Não alterar o formato numérico sequencial (`XXXX_nome.py`) das migrações.

## Decisions

### Decisão 1: Resolução de caminho em camadas em `scripts/migrador.py`
Criar a função auxiliar `obter_caminho_migracoes() -> Path` que avalia em ordem de prioridade:
1. `sys._MEIPASS / "migracoes"`: Se rodando em bundle PyInstaller com `sys.frozen`.
2. `Path(__file__).resolve().parent.parent / "migracoes"`: Se executando a partir do repositório Git (ambiente de desenvolvimento/testes).
3. `GerenciadorCaminhos().obter_caminho_base_repo() / "migracoes"`: Fallback quando executando congelado sem bundle local ou caso o repositório sincronizado possua migrações mais recentes.

*Alternativas consideradas:* Apenas empacotar no PyInstaller. Descartada porque se o usuário sincronizar novas migrações via Git no app antes de atualizar o executável da loja, o app ficaria cego para as migrações mais novas.

### Decisão 2: Inclusão de `migracoes/` nos `datas` do PyInstaller
Em `editor/EditorAresta.spec`, adicionar explicitamente:
```python
datas += [
    (str(repo_root / "migracoes"), "migracoes"),
]
```
Garante que o executável standalone possa operar 100% offline, conforme especificado originalmente em `legacy_specs/editor_atualizacoes.md`.

### Decisão 3: Atualização forçada em `corrigir_database` e persistência do Editor
Em `scripts/preparar_submissao_lib.py:corrigir_database`:
Após chamar `aplicar_migracoes(pico_path)`, verificar se `croqui_data.get("ultima_migracao", 0) < obter_ultima_versao_migracao()`. Se for menor, atualizar o valor para a versão máxima no arquivo `croqui.yaml`. Isso previne que croquis que já estavam com schema atualizado mas com valor `0` (ou ausente) sejam submetidos sem o carimbo da versão.

### Decisão 4: Validação no CI (`serving/pr_db_validator.py`)
Implementar a função `validar_versoes_migracao(pastas_modificadas: list[Path]) -> list[str]` que:
1. Obtém a versão máxima de migração com `obter_ultima_versao_migracao()`.
2. Para cada pasta de croqui em `database/` alterada no PR, lê `croqui.yaml` e valida se `ultima_migracao == versao_maxima`.
3. Se estiver ausente, zerada ou inferior, retorna erro bloqueante com mensagem clara orientando a atualizar o campo.
4. Adicionar a pasta `migracoes` no `sparse-checkout` de `.github/workflows/pr-db-validator.yml`.

## Risks / Trade-offs

- **[Risco: Import circular entre `scripts/migrador.py` e `editor/core/storage.py`]** &rarr; *Mitigação*: Usar import lazy dentro do bloco de fallback de `obter_caminho_migracoes()`, protegendo com `try/except Exception`.
- **[Risco: CI falhar em PRs de branches antigas sem a versão 5]** &rarr; *Mitigação*: O CI do PR deve ser rigoroso para proteger a base de dados principal (`main`). A mensagem de erro instruirá claramente que a branch deve ser atualizada e o croqui revalidado.
