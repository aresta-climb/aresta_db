# pipeline-compilacao-incremental-em-memoria Specification

## Purpose
Define o pipeline de compilação e deploy incremental em memória para croquis de escalada, garantindo leitura única por arquivo fonte, sincronização incremental de mídias e thumbnails via metadados de sistema de arquivos (`stat`) e hashes `hashlib.file_digest`, isolamento estrito de escopo em compilações parciais (`--target`) e atualização em memória do relatório de saúde dos croquis.

## Requirements

### Requirement: Carregamento Único em Memória por Croqui Compilado
O pipeline de preparação e compilação (`corrigir_database` e `compilar_croqui` em `scripts/preparar_submissao_lib.py`) SHALL carregar o arquivo `croqui.yaml` e cada arquivo Markdown (`.md`) pertencente ao croqui uma única vez do disco para a memória RAM, conduzindo o saneamento de UIDs, migração de caminhos de imagens, conversão de coordenadas E7, desduplicação de referências, coleta de arquivos referenciados, auditoria de UIDs e expansão para Protobuf diretamente sobre as estruturas em memória, e regravando em `database/<id>` exclusivamente os arquivos que sofrerem modificação real.

#### Scenario: Compilação de croqui já saneado sem modificações no database
- **WHEN** `deploy()` ou `corrigir_database()` é executado sobre um croqui cujos arquivos `.yaml` e `.md` já estão com UIDs válidos, coordenadas em E7 e comentários de licença SPDX corretos
- **THEN** o sistema lê cada arquivo `.yaml` e `.md` do croqui apenas uma vez para a memória, conclui todas as verificações e a geração de `compilado.binarypb` a partir dos dados em RAM e não realiza nenhuma operação de escrita na pasta `database/<id>`.

#### Scenario: Reuso em memória dos dados compilados para validações pós-compilação
- **WHEN** `compilar_croqui()` finaliza a construção do dicionário compilado e a serialização de `compilado.binarypb`
- **THEN** `passo_a_compilar_croquis()` executa todas as verificações de integridade (IDs inteiros, nomes duplicados de escalada, escaladas sem mapa, imagens inexistentes, mapas duplicados e títulos H1 em descrição) diretamente sobre o dicionário retornado em memória, sem reler arquivos do disco.

### Requirement: Sincronização Incremental de Imagens, Anexos e Checksums via `stat`
Durante a compilação de um croqui para `generated/<id>`, o sistema SHALL preservar o diretório de destino existente (sem executar `force_rmtree` na pasta do croqui), sincronizar arquivos de `imagens/` e `anexos/` comparando `(st_mtime_ns, st_size)` entre origem e destino, copiar via `shutil.copy2` e calcular o SHA-256 via `hashlib.file_digest` apenas para arquivos novos ou cujo `(st_mtime_ns, st_size)` tenha divergido (reaproveitando o `checksum_sha256` registrado no `compilado.binarypb` anterior para arquivos intocados), e remover do destino quaisquer arquivos que não existam mais na pasta de origem.

#### Scenario: Salvamento ou recompilação sem alteração nas imagens do croqui
- **WHEN** um croqui já compilado anteriormente em `generated/<id>` é recompilado sem que suas imagens em `database/<id>/imagens/` tenham sido alteradas e sem a flag `--force`
- **THEN** o sistema verifica a igualdade de `(st_mtime_ns, st_size)` entre origem e destino, não copia nenhum arquivo de imagem e reutiliza os hashes `checksum_sha256` presentes em `arquivos_externos` do `compilado.binarypb` anterior sem ler os bytes das imagens do disco.

#### Scenario: Adição, edição ou exclusão de imagem em `database/<id>/imagens/`
- **WHEN** uma imagem é adicionada ou modificada em `database/<id>/imagens/` (alterando seu `st_mtime_ns` ou `st_size`) ou uma imagem antiga é removida
- **THEN** o sistema copia com `shutil.copy2` e calcula o SHA-256 com `hashlib.file_digest` apenas para a imagem nova/modificada, preserva as demais imagens intactas e remove de `generated/<id>/imagens/` a imagem que deixou de existir na origem.

### Requirement: Geração Incremental de Thumbnail por Timestamp Sincronizado e Flag `--force`
A função `processar_thumbnail` SHALL estampar na thumbnail gerada (`generated/thumbnails/<id>.webp`) os metadados de tempo da imagem de origem (`shutil.copystat`) logo após criá-la e, em execuções subsequentes sem `--force`, SHALL pular o reprocessamento no Pillow quando a thumbnail de destino existir e possuir exatamente o mesmo `st_mtime_ns` da imagem de origem apontada por `caminho_thumbnail`. Quando a flag `--force` (ou `--force-thumbnails`) for informada, o sistema SHALL reprocessar a thumbnail e recalcular todos os hashes SHA-256 de imagens e anexos independentemente do `stat()`.

#### Scenario: Compilação normal com thumbnail já atualizada
- **WHEN** `deploy()` é executado (via CLI ou salvamento no Aresta Editor) e `generated/thumbnails/<id>.webp` possui o mesmo `st_mtime_ns` da imagem apontada em `caminho_thumbnail`
- **THEN** o sistema mantém a thumbnail existente sem invocar o Pillow.

#### Scenario: Alteração da imagem de capa ou troca do `caminho_thumbnail`
- **WHEN** a imagem apontada em `caminho_thumbnail` é editada ou o campo `caminho_thumbnail` no `croqui.yaml` passa a apontar para outra imagem com `st_mtime_ns` distinto
- **THEN** o sistema detecta a divergência de `st_mtime_ns`, regenera `generated/thumbnails/<id>.webp` e sincroniza seu timestamp com a nova imagem de origem via `shutil.copystat`.

#### Scenario: Execução com flag `--force`
- **WHEN** `deploy_generated.py` é executado com `--force` (ou `force=True` / `force_thumbnails=True`)
- **THEN** o sistema recalcula o SHA-256 de todas as imagens e anexos via `hashlib.file_digest`, substitui no destino qualquer arquivo cujo hash divirja e regenera a thumbnail no Pillow.

### Requirement: Isolamento de Escopo em Compilações com `--target`
Quando `target_paths` (`--target` ou argumentos posicionais) for especificado em `deploy()`, o sistema SHALL carregar apenas os croquis indicados nos alvos — abstendo-se de ler ou fazer parse dos arquivos `croqui.yaml` dos demais croquis em `database/` — e, na geração de `arquivos_serving.yaml` (`passo_d_gerar_manifesto_serving`), SHALL preservar os registros e checksums existentes no `arquivos_serving.yaml` anterior para todos os croquis que não fizeram parte de `target_paths`, recalculando apenas as entradas dos croquis efetivamente compilados e dos arquivos globais (`indice.binarypb`, `indice.yaml`, `catalogo.db`).

#### Scenario: Compilação de um único croqui via `--target`
- **WHEN** `deploy()` é invocado com `target_paths=["database/meu_croqui"]`
- **THEN** o sistema lê apenas os arquivos de `database/meu_croqui`, preserva os metadados dos demais croquis a partir de `indice.binarypb` e `arquivos_serving.yaml` anteriores e não abre os arquivos `croqui.yaml` nem `compilado.binarypb` dos outros croquis não modificados.

### Requirement: Ausência de Artefatos Legados de Debug (`compilado.yaml` e `compilado.md`)
O pipeline de compilação e deploy SHALL gerar exclusivamente `compilado.binarypb` (além de `imagens/` e `anexos/`) dentro de `generated/<id>/`, abstendo-se de criar ou indexar os arquivos `compilado.yaml` e `compilado.md`.

#### Scenario: Estrutura do diretório compilado de um croqui
- **WHEN** um croqui é compilado por `deploy()` ou `compilar_croqui()`
- **THEN** o diretório de saída contém `compilado.binarypb` (e as pastas de mídia correspondentes), sem gerar `compilado.yaml` ou `compilado.md`.

### Requirement: Atualização em Memória e Incremental do Relatório de Saúde (`STATUS_CROQUIS.md`)
O módulo `scripts/medir_saude_croquis.py` SHALL expor funções de biblioteca invocáveis diretamente no mesmo processo Python por `deploy_generated.py` e pelo Editor (sem `subprocess.run`), realizando um único parse por croqui avaliado e, quando um subconjunto de croquis (`alvos`) for informado e `STATUS_CROQUIS.md` já existir, SHALL atualizar apenas as linhas correspondentes aos croquis avaliados e recalcular os contadores agregados do cabeçalho da tabela a partir das linhas em memória, sem ler do disco os demais croquis da pasta `database/`.

#### Scenario: Atualização incremental de `STATUS_CROQUIS.md` após compilar um croqui
- **WHEN** `deploy_generated.py` compila um croqui específico com `--status` ativo e `STATUS_CROQUIS.md` já existe
- **THEN** o sistema avalia a saúde apenas do croqui compilado reutilizando seus dados em memória, substitui apenas a linha daquele croqui na tabela de `STATUS_CROQUIS.md`, recalcula os totais do cabeçalho da tabela e salva o arquivo em LF se houver mudança.
