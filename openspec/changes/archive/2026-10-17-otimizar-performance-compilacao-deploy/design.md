# Design

## Context

Conforme detalhado em `proposal.md` (seção *Why*), a compilação de um croqui em `scripts/deploy_generated.py` (chamada tanto via CLI quanto pelo salvamento do Aresta Editor em `editor/core/workspace.py` e `editor/core/croqui_experimental.py`) realiza atualmente ~6 a 8 ciclos de leitura/parse por arquivo `.yaml`/`.md`, mistura `ruamel.yaml` com `PyYAML` em Python puro, destrói e recopia `generated/<id>` inteiro a cada execução, gera artefatos de debug obsoletos (`compilado.yaml` e `compilado.md`), varre todos os 52 croquis mesmo quando `--target` é informado e dispara `scripts/medir_saude_croquis.py` via `subprocess.run` lendo `croqui.yaml` 8 vezes por croqui.

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de compilação de um croqui individual (`--target` e salvamento no Editor) de ~11–12s para uma fração de segundo (~0.2s–0.5s).
- Garantir leitura única do disco para a RAM dos arquivos `.yaml` e `.md` do croqui compilado e escrita condicional apenas do que foi modificado.
- Padronizar 100% da leitura e escrita de YAML no binding em C da LibYAML (`CSafeLoader`/`CSafeDumper`), removendo `ruamel.yaml` do projeto.
- Evitar leituras e cópias desnecessárias de imagens e thumbnails em máquinas com discos mais lentos ou antivírus ativos utilizando comparação de `stat()` (`st_mtime_ns` e `st_size`) combinada com os hashes SHA-256 já persistidos no `compilado.binarypb` anterior.
- Executar a atualização de `STATUS_CROQUIS.md` em memória no mesmo processo Python e de forma incremental para os croquis compilados.
- Alinhar o indicador `"Salvando..."` no canto inferior direito da `AreaPrincipal`.

**Non-Goals:**
- Preservar comentários arbitrários no meio de arquivos YAML (apenas as duas linhas padrão de cabeçalho SPDX/Copyright no topo são mantidas).
- Alterar o contrato binário Protobuf de `compilado.binarypb`, `indice.binarypb` ou o schema SQLite de `catalogo.db`.

## Decisions

### 1. Centralização de YAML em `LibYAML` (`CSafeLoader` / `CSafeDumper`) e Remoção de `ruamel.yaml`
- **Decisão**: Criar e exportar em `editor/core/serializacao_util.py` funções canônicas `carregar_yaml(conteudo_ou_stream)` e `serializar_yaml(dados)` que utilizam `yaml.CSafeLoader` e `yaml.CSafeDumper` (com fallback automático para `yaml.SafeLoader` e `yaml.SafeDumper`), registrando `representar_string_yaml` em todos os dumpers suportados. Toda escrita de `croqui.yaml` e de frontmatter em `scripts/markdown_frontmatter_lib.py` injetará as duas linhas de cabeçalho `# SPDX-License-Identifier: ODbL-1.0` e `# Copyright (C) 2026 Aresta Climb Contributors` no topo e gravará via `escrever_texto_se_modificado`.
- **Racional**: Em benchmarks reais sobre os 38 arquivos `.md` de `serra_do_lenheiro`, `CSafeLoader` + `CSafeDumper` foi **13.3x mais rápido** que `ruamel.yaml` (`249 ms` vs `3329 ms`) e **6.2x mais rápido** que `PyYAML` em Python puro (`249 ms` vs `1536 ms`), produzindo **zero diferenças** de formatação em relação ao `SafeDumper` atual. Além disso, eliminar `ruamel.yaml` resolve divergências de quebra de linha (`width=120` vs `width=80`) e reduz o tamanho do executável empacotado pelo PyInstaller.
- **Alternativas consideradas**: Manter `ruamel.yaml` apenas em `sanear_uids_croqui` com fast-path de leitura em `CSafeLoader`. Rejeitado porque ainda manteria uma dependência externa desnecessária e duas formatações de dump distintas quando um novo UID precisasse ser gerado.

### 2. Contexto de Croqui em Memória (`CacheArquivosCroqui` / Passagem Única)
- **Decisão**: Durante o ciclo de `corrigir_database` e `compilar_croqui` de um croqui:
  1. Carregar `croqui.yaml` e todos os arquivos `.md` do diretório do croqui uma única vez em memória.
  2. Executar `aplicar_migracoes`, `sanear_uids_croqui`, correção de caminhos de imagens/coordenadas E7, `desduplicar_referencias_no_md`, `limpar_arquivos_nao_utilizados` e `auditar_uids_database` operando sobre os dicionários e corpos Markdown carregados em memória (ou recarregando somente se uma migração externa de script tocar no disco), gravando de volta apenas os arquivos marcados como modificados (`escrever_texto_se_modificado`).
  3. Retornar ou compartilhar a estrutura em memória com `compilar_croqui` para expandir os setores/grupos/botões/mapas gerais sem reabrir nem refazer parse dos arquivos `.md` do disco.
  4. Em `passo_a_compilar_croquis`, passar o dicionário `croqui_data` retornado por `compilar_croqui` diretamente para todas as funções de validação (`_check_integer_ids`, `verificar_nomes_duplicados_de_escalada`, `verificar_escaladas_sem_mapa`, `verificar_imagens_inexistentes`, `verificar_mapas_duplicados`, `verificar_titulos_em_descricao_setor_grupo`).
- **Racional**: Elimina 5 a 7 releituras e parses redundantes de cada `.md` e do `croqui.yaml` no mesmo ciclo de compilação.

### 3. Sincronização Incremental de Imagens, Anexos e Thumbnails via `stat()` + `compilado.binarypb` Anterior
- **Decisão**:
  - Não executar `force_rmtree(dest_dir)` em `generated/<id>` no início de `passo_a_compilar_croquis`.
  - Antes de sincronizar imagens e anexos, se `generated/<id>/compilado.binarypb` já existir e `force=False`, ler seus registros `arquivos_externos` (`{caminho: checksum_sha256}`) em ~0.5 ms.
  - Para cada arquivo em `database/<id>/imagens/*.webp` (e `anexos/**/*`):
    - Comparar `src.stat()` com `dst.stat()` (`st_mtime_ns` e `st_size`).
    - Se `not force` e `dst.exists()` e `src_stat.st_mtime_ns == dst_stat.st_mtime_ns` e `src_stat.st_size == dst_stat.st_size` e o caminho já possuir `checksum_sha256` válido no `compilado.binarypb` anterior: **não copiar o arquivo e reaproveitar o `checksum_sha256` anterior sem abrir nem ler a imagem**.
    - Caso contrário (ou se `force=True`): copiar com `shutil.copy2(src, dst)` (que preserva `st_mtime_ns` e `st_size` via `_winapi.CopyFile2` + `copystat`) e calcular o hash com `hashlib.file_digest(f, "sha256").hexdigest()`.
  - Remover de `generated/<id>/imagens/` e `generated/<id>/anexos/` quaisquer arquivos ou diretórios órfãos que não existam mais na origem (bem como remover `compilado.yaml` e `compilado.md` residuais caso existam).
  - Em `atualizar_dimensoes_mapas`: só abrir a imagem com `Image.open()` se `largura_mapa` ou `altura_mapa` não estiverem preenchidos como inteiros positivos (ou se a imagem tiver sido modificada).
  - Em `processar_thumbnail`: logo após salvar `generated/thumbnails/<id>.webp`, chamar `shutil.copystat(src_path, dest_path)`. Em execuções futuras com `force=False`, pular o processamento do Pillow se `dest_path.exists()` e `dest_path.stat().st_mtime_ns == src_path.stat().st_mtime_ns`. No Editor (`LocalRepoWorkspace` e `GerenciadorCroquiExperimental`), passar `force_thumbnails=False` por padrão.
- **Racional**: Em computadores de usuários com SSDs de entrada, HDDs ou Windows Defender ativo, abrir e ler dezenas de megabytes de imagens a cada salvamento é custoso. Combinar `stat()` com os hashes já salvos no `compilado.binarypb` anterior reduz a leitura de bytes de imagens para **zero** quando nenhuma foto foi editada, mantendo 100% de precisão ao detectar edições ou trocas de arquivo.

### 4. Remoção de `compilado.yaml` e `compilado.md`
- **Decisão**: Remover a geração de `compilado.yaml` e `compilado.md` do pipeline (`deploy_generated.py` e `preparar_submissao_lib.py`), excluir `scripts/gerar_compilado_md.py` e `scripts/gerar_compilado_md_test.py`, e remover a indexação desses dois arquivos em `passo_d_gerar_manifesto_serving`.
- **Racional**: Nenhum componente de produção (Editor, App Mobile, Catálogo SQLite ou Coleta de Betas) consome esses arquivos, que existiam apenas para depuração histórica e custavam ~0.6s por croqui compilado.

### 5. Isolamento de `--target` e Manifesto Incremental (`arquivos_serving.yaml`)
- **Decisão**:
  - Quando `target_paths` for informado em `deploy()`, carregar exclusivamente os croquis de `target_paths` via `carregar_um_croqui()`, sem chamar `encontrar_croquis()` sobre toda a pasta `database/`.
  - Em `passo_d_gerar_manifesto_serving`, quando em modo parcial (`target_paths`), carregar o `arquivos_serving.yaml` existente e reaproveitar todas as entradas pertencentes aos croquis preservados (`<id_preservado>/*` e `thumbnails/<id_preservado>.webp`), lendo `compilado.binarypb` apenas para os croquis recém-compilados.
- **Racional**: Transforma operações que eram $O(N_{\text{todos os croquis}})$ em $O(N_{\text{alvos}})$, economizando ~1.1s em cada compilação individual.

### 6. `medir_saude_croquis.py` como Biblioteca em Memória e Atualização Incremental
- **Decisão**:
  - Refatorar `scripts/medir_saude_croquis.py` para avaliar um croqui fazendo **um único carregamento** de `croqui.yaml` e dos seus `.md` (ou recebendo os dados já carregados em memória pelo `deploy_generated.py`).
  - Substituir as chamadas `subprocess.run([sys.executable, ...])` em `deploy_generated.py` e `editor/core/workspace.py` por chamadas diretas de função em memória (`atualizar_relatorio_saude_croquis(alvos=...)`).
  - Quando `alvos` for informado e `STATUS_CROQUIS.md` já existir no disco, fazer parse das linhas da tabela Markdown existente, atualizar/inserir em ordem alfabética apenas as linhas dos croquis em `alvos`, recalcular os contadores do cabeçalho (`Publicado (X/Y)`, etc.) a partir das linhas em memória e salvar via `salvar_relatorio_saude_se_modificado`.
- **Racional**: Elimina o custo de spawn de processo Python no Windows (~0.3s) e elimina os 416 parses de `croqui.yaml` + leitura de todos os `.md` dos 52 croquis (~7.1s), reduzindo a atualização do `STATUS_CROQUIS.md` para < 10 ms.

### 7. Posicionamento do Indicador `"Salvando..."` no Canto Inferior Direito
- **Decisão**: Em `editor/legacy_views/area_principal.py`, posicionar `self.label_status_salvamento` em `(self.width() - self.label_status_salvamento.width() - 20, self.height() - self.label_status_salvamento.height() - 20)` (e atualizar no `resizeEvent` se visível), alinhando-o com as coordenadas usadas por `NotificacaoToast.posicionar_no_canto`.
- **Racional**: Mantém o foco visual do usuário em um único ponto da tela durante a transição entre `"Salvando..."` e `"Croqui salvo e compilado com sucesso!"`.

## Risks / Trade-offs

- **[Risco] Comentários manuais no meio de arquivos YAML serem descartados ao salvar** → **Mitigação**: Decisão consciente alinhada ao comportamento que o Aresta Editor já possuía; a base `database/` já utiliza apenas os cabeçalhos fixos SPDX/Copyright no topo, que são garantidos automaticamente pelas funções centralizadas de serialização.
- **[Risco] Alteração externa de bytes de imagem mantendo o mesmo `st_mtime_ns` e `st_size`** → **Mitigação**: A flag `--force` permite forçar o recálculo integral de `sha256` e a regeneração de thumbnails a qualquer momento.
- **[Risco] Testes existentes que verificavam a existência de `compilado.yaml` ou `compilado.md`** → **Mitigação**: Atualizar os testes de integração/unidade para validar `compilado.binarypb` e o dicionário retornado por `compilar_croqui()`, removendo o teste espelhado do módulo deletado `gerar_compilado_md_test.py`.
