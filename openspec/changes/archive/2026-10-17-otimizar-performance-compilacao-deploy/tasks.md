# Tasks

## 1. Centralização de Serialização YAML em LibYAML (`CSafeLoader`/`CSafeDumper`) e Remoção de `ruamel.yaml`

- [x] 1.1 Escrever testes comportamentais em `editor/core/serializacao_util_test.py` e `scripts/markdown_frontmatter_lib_test.py` validando `carregar_yaml` e `serializar_yaml` com `CSafeLoader`/`CSafeDumper`, formatação de strings multilinhas/numéricas e injeção automática do cabeçalho de licença SPDX/Copyright, verificando falha inicial (Red) e aprovação após implementar em `editor/core/serializacao_util.py` e `scripts/markdown_frontmatter_lib.py` (Green) via `uv run pytest editor/core/serializacao_util_test.py scripts/markdown_frontmatter_lib_test.py`.
- [x] 1.2 Substituir o uso de `ruamel.yaml` e `yaml.safe_load`/`yaml.dump` em `scripts/gerenciar_uids_lib.py`, `scripts/migrador.py`, `scripts/recalcular_coordenadas.py` e migrações legadas (`migracoes/`) pelas funções centralizadas de `serializacao_util` e `markdown_frontmatter_lib`, atualizando seus respectivos arquivos `*_test.py` (removendo eventuais mocks internos) e verificando com `uv run pytest scripts/gerenciar_uids_lib_test.py scripts/migrador_test.py scripts/recalcular_coordenadas_test.py migracoes/`.
- [x] 1.3 Remover `ruamel.yaml` de `pyproject.toml` e `editor/build.py`, atualizar `uv.lock` com `uv lock` e verificar que `uv run pytest editor/build_test.py` passa sem referências a `ruamel`.

## 2. Pipeline de Compilação em Memória e Remoção de `compilado.yaml` / `compilado.md`

- [x] 2.1 Atualizar e expandir os testes comportamentais em `scripts/preparar_submissao_lib_test.py` para exercitar o carregamento único em memória de `croqui.yaml` e `*.md` durante `corrigir_database` e `compilar_croqui`, a reutilização em memória sem releitura do disco, a abertura de imagens em `atualizar_dimensoes_mapas` apenas quando `largura_mapa`/`altura_mapa` estiverem ausentes e a não geração de `compilado.yaml`, verificando com `uv run pytest scripts/preparar_submissao_lib_test.py`.
- [x] 2.2 Remover os arquivos `scripts/gerar_compilado_md.py` e `scripts/gerar_compilado_md_test.py`, eliminar referências a `compilado.yaml` e `compilado.md` em `scripts/deploy_generated.py`, `editor/core/croqui_experimental.py`, `.agents/skills/preencher_croqui_yaml/SKILL.md` e `.agents/workflows/processar_croqui_completo.md`, e verificar a ausência de importações quebradas nos testes de `editor/core/croqui_experimental_test.py` e `editor/core/salvamento_estruturas_vazias_integracao_test.py`.

## 3. Sincronização Incremental de Imagens/Thumbnails via `stat()` e Isolamento de `--target`

- [x] 3.1 Escrever testes comportamentais em `scripts/deploy_generated_test.py` (substituindo mocks de código interno por diretórios temporários reais `tmp_path` conforme `AGENTS.md`) para validar: (a) cálculo de SHA-256 via `hashlib.file_digest`, (b) sincronização incremental de `imagens/` e `anexos/` sem `force_rmtree` reaproveitando `checksum_sha256` do `compilado.binarypb` anterior quando `(st_mtime_ns, st_size)` não muda e removendo órfãos, (c) geração incremental de thumbnail sincronizando timestamp via `shutil.copystat`, (d) flag `--force` para forçar recálculo de hashes e regeneração de thumbnails, e (e) isolamento estrito de `--target` no carregamento de croquis e na preservação incremental de `arquivos_serving.yaml`.
- [x] 3.2 Implementar em `scripts/deploy_generated.py`, `editor/core/workspace.py` e `editor/core/croqui_experimental.py` as otimizações de sincronização incremental, flag `--force`, execução das validações pós-compilação sobre o dicionário em memória e `force_thumbnails=False` por padrão no salvamento do Editor, verificando que `uv run pytest scripts/deploy_generated_test.py editor/core/workspace_test.py editor/core/croqui_experimental_test.py` passa com 100% de cobertura nos módulos alterados.

## 4. Medição de Saúde (`STATUS_CROQUIS.md`) em Memória e Incremental

- [x] 4.1 Escrever testes comportamentais em `scripts/medir_saude_croquis_test.py` para validar a avaliação de saúde com parse único por croqui (e aceitando dados já carregados em memória) e a atualização incremental de linhas específicas na tabela de `STATUS_CROQUIS.md` com recálculo automático dos contadores do cabeçalho, verificando com `uv run pytest scripts/medir_saude_croquis_test.py`.
- [x] 4.2 Implementar a interface de biblioteca em memória e atualização incremental em `scripts/medir_saude_croquis.py` e substituir o `subprocess.run` em `scripts/deploy_generated.py` e `editor/core/workspace.py` pela chamada direta em memória, validando com `uv run pytest scripts/medir_saude_croquis_test.py scripts/deploy_generated_test.py editor/core/workspace_test.py`.

## 5. Alinhamento do Indicador `"Salvando..."` no Canto Inferior Direito do Editor

- [x] 5.1 Atualizar e adicionar teste comportamental em `editor/legacy_views/area_principal_test.py` verificando que `label_status_salvamento` (`"Salvando..."`) é posicionado no canto inferior direito da `AreaPrincipal` (com margem de 20px das bordas direita e inferior) ao iniciar o salvamento e ao redimensionar a janela, e implementar o ajuste em `editor/legacy_views/area_principal.py`, verificando com `uv run pytest editor/legacy_views/area_principal_test.py`.

## 6. Verificação Integrada e Qualidade Global

- [x] 6.1 Executar `openspec validate otimizar-performance-compilacao-deploy`, linter/formatador (`uv run ruff check` e `uv run mypy`) e a suíte de testes e cobertura dos módulos afetados para assegurar 100% de cobertura comportamental e conformidade integral com o `AGENTS.md`.

