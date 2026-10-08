# Proposal

## Why

Atualmente, croquis criados ou editados no Aresta Editor podem ter o campo `ultima_migracao` gravado como `0` em `croqui.yaml`, em vez de refletir a última migração realizada no catálogo (atualmente versão 5). Isso ocorre porque os scripts de migração em `migracoes/` não são empacotados pelo PyInstaller (`editor/EditorAresta.spec`), e `scripts/migrador.py` não faz fallback para o repositório base clonado localmente quando executado a partir de um aplicativo empacotado. Além disso, o validador de Pull Requests do CI (`serving/pr_db_validator.py`) não valida a consistência de `ultima_migracao`, permitindo que propostas de croqui desatualizadas cheguem para revisão e sejam aceitas inadvertidamente.

Garantir que a versão de migração esteja sempre sincronizada e validada previne regressões de dados, inconsistências estruturais e retrabalho manual de correção durante revisões de PRs.

## What Changes

- **Empacotamento e Resolução de Migrações**:
  - Adiciona o diretório `migracoes/` aos dados incluídos (`datas`) no arquivo de especificação do PyInstaller (`editor/EditorAresta.spec`).
  - Torna `scripts/migrador.py` resiliente a ambientes empacotados: além do diretório relativo ao script, realiza fallback para o diretório `migracoes/` do repositório base local mantido em `GerenciadorCaminhos().obter_caminho_base_repo()` quando executado congelado/empacotado.
- **Ciclo de Vida de Croquis Experimentais**:
  - Garante que a criação de novo croqui (`criar_novo_croqui`), a importação a partir de oficial e o salvamento/extração de dados garantam que `ultima_migracao` seja cravada com a última versão de migração disponível (`obter_ultima_versao_migracao()`).
  - Atualiza a rotina de saneamento de database (`corrigir_database` em `scripts/preparar_submissao_lib.py`) para assegurar que `croqui.yaml` sempre receba a versão mais recente após a execução do motor de migrações, mesmo que o arquivo original não possuísse a chave ou estivesse zerado.
- **Validador de Pull Requests (CI)**:
  - Adiciona verificação no validador do banco de dados (`serving/pr_db_validator.py`) para exigir que todo `croqui.yaml` submetido tenha `ultima_migracao` igual à versão máxima retornada por `obter_ultima_versao_migracao()`.
  - Inclui a pasta `migracoes` no `sparse-checkout` do workflow `.github/workflows/pr-db-validator.yml` para viabilizar essa validação em ambiente de CI.

## Capabilities

### New Capabilities
Nenhuma nova capacidade criada.

### Modified Capabilities
- `croqui-experimental-format`: Atualiza os requisitos da estrutura de `database/` para assegurar que todo croqui experimental persistido ou submetido possua `ultima_migracao` sincronizada com a última versão de migração do repositório.
- `protobuf-migrations`: Atualiza os requisitos do motor de migração sequencial para garantir que a localização dos scripts de migração funcione de forma transparente tanto em desenvolvimento quanto no aplicativo empacotado/congelado.
- `ci-cd-workflow-pr`: Atualiza o validador de Pull Requests para rejeitar croquis modificados cuja `ultima_migracao` esteja zerada ou desatualizada em relação ao catálogo oficial.

## Impact

- **Código Afetado**:
  - `editor/EditorAresta.spec`: Inclusão de `migracoes/` nos `datas`.
  - `scripts/migrador.py`: Resolução dinâmica do caminho de migrações (`caminho_base_repo` fallback).
  - `editor/core/croqui_experimental.py`: Garantia de versão máxima na inicialização e cópia.
  - `scripts/preparar_submissao_lib.py`: Garantia de preenchimento de `ultima_migracao` em `corrigir_database`.
  - `serving/pr_db_validator.py`: Validação de `ultima_migracao` em croquis submetidos.
  - `.github/workflows/pr-db-validator.yml`: Adição de `migracoes` no `sparse-checkout`.
- **Compatibilidade**: Nenhuma quebra de retrocompatibilidade; os croquis oficiais já utilizam a versão 5.
- **Dependências**: Nenhuma nova dependência introduzida.
