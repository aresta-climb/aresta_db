# Design

## Context

Conforme descrito em `proposal.md`, salvar um croqui pelo Editor Aresta no Windows faz com que arquivos não editados apareçam como modificados tanto no `git status` local quanto em commits de Pull Requests. O repositório já adota `.gitattributes` com `* text=auto eol=lf`, portanto o padrão canônico em disco e no índice do Git para todos os sistemas operacionais é `LF` (`\n`).

## Goals / Non-Goals

**Goals:**
- Garantir que exista uma única implementação de `_str_representer` e escrita textual em `LF` compartilhada entre `editor/` e `scripts/`.
- Evitar I/O redundante em arquivos `.md` e `.yaml` cujo conteúdo normalizado em `LF` não mudou, preservando `mtime` e evitando invalidação desnecessária do cache do Git.
- Garantir que `pygit2` opere sempre com `core.autocrlf = False` tanto no repositório base quanto nos repositórios de croquis experimentais.
- Evitar atualizações de timestamp em `STATUS_CROQUIS.md` quando a tabela de saúde não mudou.

**Non-Goals:**
- Alterar o formato de dados Protobuf ou a estrutura dos arquivos `.md`/`.yaml` do banco de dados.
- Introduzir escrita em `CRLF` no Windows (pois isso conflitaria com `* text=auto eol=lf` em `.gitattributes`).

## Decisions

### 1. Centralização de `representar_string_yaml` e `escrever_texto_se_modificado` em `editor/core/serializacao_util.py`
- **Decisão**: Definir em `editor/core/serializacao_util.py` (e reexportar/usar em `scripts/markdown_frontmatter_lib.py` e `scripts/preparar_submissao_lib.py`):
  - `representar_string_yaml(dumper, data)` e `configurar_yaml_representer()`:
    1. Se `"\n" in data`, usa `style="|"`.
    2. Se `data.isdigit() or (data.startswith("-") and data[1:].isdigit())`, usa `style="'"`.
    3. Caso contrário, `style=None`.
    Registra em `yaml.Dumper` e `yaml.SafeDumper`.
  - `escrever_texto_se_modificado(caminho: Path, conteudo: str) -> bool`:
    Normaliza `conteudo` substituindo `\r\n` por `\n`. Se `caminho.exists()`, lê os bytes atuais; se os bytes atuais forem exatamente iguais a `conteudo_lf.encode("utf-8")` (ou se o texto decodificado normalizado em `\n` for igual **e** o arquivo no disco já não contiver `\r\n`), não reescreve o arquivo e retorna `False`. Caso o arquivo no disco contenha `\r\n` legado ou conteúdo diferente, grava em UTF-8 com `newline="\n"` e retorna `True`.
  - *Nota importante sobre arquivos com `\r\n` legado quando o conteúdo lógico é igual*:
    Se durante `CroquiModel.extrair_arquivos_e_serializar` compararmos o conteúdo lógico (`conteudo_atual.replace("\r\n", "\n") == conteudo_novo_lf`), **não reescrever** um setor que não foi editado evita tocar nos outros setores caso o clone local ainda tenha algum arquivo com `CRLF`. Já a renormalização do repositório deve ser feita no nível do Git (`core.autocrlf = False` + normalização do índice). Assim, `escrever_texto_se_modificado` comparará `conteudo_atual.replace("\r\n", "\n") == conteudo_novo_lf` para decidir se houve mudança lógica de conteúdo; quando houver mudança (ou arquivo novo), gravará sempre com `newline="\n"`.
- **Alternativas consideradas**:
  - Usar classes `Dumper` customizadas em cada chamada `yaml.dump(..., Dumper=ArestaDumper)`: exigiria alterar todas as chamadas e mocks de `yaml.dump` nos testes existentes (`worker_test.py`, `area_principal_test.py`, `deploy_generated_test.py`). Registrar a função unificada em `yaml.Dumper` e `yaml.SafeDumper` mantém 100% de compatibilidade com todos os testes que fazem `patch("yaml.dump")` e elimina a divergência porque ambos os módulos registram exatamente a mesma função.

### 2. Configuração explícita de `core.autocrlf = False` no `pygit2`
- **Decisão**: Em `GerenciadorSincronizacao.clonar`, `GerenciadorSincronizacao.fazer_checkout_main_upstream` (`editor/core/sync.py`) e `GerenciadorCroquiExperimental._criar_estrutura_croqui` (`editor/core/croqui_experimental.py`), definir `repo.config["core.autocrlf"] = False` (além de `repo.config["core.longpaths"] = True`).
- **Racional**: Repositórios de croquis experimentais criados em `%LOCALAPPDATA%/EditorAresta/croquis/<uuid>` não possuem `.gitattributes` próprio e herdam o `core.autocrlf=true` do Git for Windows se não for configurado explicitamente no repositório local.

### 3. Comparação de arquivos textuais em `ServicoSubmissao`
- **Decisão**: Em `ServicoSubmissao` (`editor/core/servico_submissao.py`), criar um método auxiliar `_arquivos_iguais(arq1: Path, arq2: Path) -> bool` usado por `obter_arquivos_modificados` e `_espelhar_diretorio`:
  - Para extensões textuais (`.md`, `.yaml`, `.yml`, `.json`), compara o conteúdo textual normalizando `\r\n` para `\n` (com fallback para `filecmp.cmp` em caso de erro de decodificação UTF-8).
  - Para arquivos binários (imagens `.webp`, `.pdf`, etc.), mantém `filecmp.cmp(arq1, arq2, shallow=False)`.

### 4. Preservação de timestamp em `STATUS_CROQUIS.md`
- **Decisão**: Em `scripts/medir_saude_croquis.py`, extrair a tabela a partir do marcador `"| Croqui |"` no arquivo `STATUS_CROQUIS.md` existente (normalizando `\r\n` para `\n`). Se a tabela existente for igual a `markdown_output.strip()` e o arquivo existente já estiver em `LF`, não reescrever o arquivo. Quando escrever, usar `newline="\n"`.

## Risks / Trade-offs

- **[Risco] Testes existentes que fazem mock de `open` ou `yaml.dump`** → Mitigação: Manter a assinatura padrão de `yaml.dump` com o representer unificado e verificar os testes unitários de `croqui_model_test.py`, `worker_test.py` e `preparar_submissao_lib_test.py`.
- **[Risco] Clones locais antigos ainda com `size` de `CRLF` no `.git/index`** → Mitigação: Executar `git add --renormalize .` / atualizar o índice local e garantir `newline="\n"` em todas as escritas.
