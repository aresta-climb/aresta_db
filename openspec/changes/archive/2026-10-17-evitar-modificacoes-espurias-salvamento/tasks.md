# Tasks

## 1. Utilitários Unificados de Serialização YAML e Escrita Condicional em LF

- [x] 1.1 Escrever testes unitários em `editor/core/serializacao_util_test.py` para `representar_string_yaml`, `configurar_yaml_representer` e `escrever_texto_se_modificado` (cobrindo strings multilinhas com `|`, dígitos positivos/negativos com `'`, escrita em `LF` e não-reescrita quando o conteúdo normalizado não muda) e verificar que falham (Red)
- [x] 1.2 Implementar `representar_string_yaml`, `configurar_yaml_representer` e `escrever_texto_se_modificado` em `editor/core/serializacao_util.py` e verificar 100% de cobertura em `editor/core/serializacao_util_test.py` (Green)

## 2. Aplicação no Modelo do Editor, Worker e Scripts de Compilação

- [x] 2.1 Escrever testes em `editor/models/croqui_model_test.py`, `editor/core/worker_test.py`, `scripts/markdown_frontmatter_lib_test.py` e `scripts/preparar_submissao_lib_test.py` garantindo preservação de `mtime` em setores não modificados, blocos `|-` em descrições multilinhas e escrita estrita em `LF` (`\n`), verificando que falham antes da mudança (Red)
- [x] 2.2 Atualizar `editor/models/croqui_model.py`, `editor/core/worker.py`, `scripts/markdown_frontmatter_lib.py` e `scripts/preparar_submissao_lib.py` para usar o representer unificado e a escrita condicional em `LF`, verificando que todos os testes unitários e de cobertura passam com 100% (Green)

## 3. Proteção contra CRLF no Git (`pygit2`) e no `ServicoSubmissao`

- [x] 3.1 Escrever testes unitários em `editor/core/sync_test.py`, `editor/core/croqui_experimental_test.py` e `editor/core/servico_submissao_test.py` verificando `core.autocrlf = False` e ignorando diferenças puras de `CRLF` vs `LF` em `obter_arquivos_modificados` e `_espelhar_diretorio` (Red)
- [x] 3.2 Implementar `core.autocrlf = False` em `editor/core/sync.py` e `editor/core/croqui_experimental.py`, e comparação textual normalizada em `editor/core/servico_submissao.py`, verificando 100% de cobertura nos testes (Green)

## 4. Atualização Condicional do `STATUS_CROQUIS.md` e Renormalização da Base

- [x] 4.1 Escrever testes unitários em `scripts/medir_saude_croquis_test.py` garantindo que `STATUS_CROQUIS.md` seja gravado em `LF` e não tenha o timestamp atualizado quando a tabela não mudar (Red)
- [x] 4.2 Implementar a verificação condicional da tabela e escrita em `LF` em `scripts/medir_saude_croquis.py`, verificando 100% de cobertura em `scripts/medir_saude_croquis_test.py` (Green)
- [x] 4.3 Renormalizar as quebras de linha da árvore de trabalho/índice do repositório e recompilar `br_mg_lagoa_santa_gruta_da_lapinha`, verificando via `git status` e `git diff` que apenas os arquivos com alterações reais permanecem modificados
