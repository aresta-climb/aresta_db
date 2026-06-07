## 1. Proto e Pipeline

- [x] 1.1 Adicionar o campo `bool publicar_croqui = 16` em `aresta_api/proto/croqui.proto`.
- [x] 1.2 Atualizar protos gerados executando `build.py` (ou gerador equivalente).
- [x] 1.3 Adicionar as flags CLI `--producao` e `--no-producao` com `argparse.BooleanOptionalAction(default=True)` em `scripts/deploy_generated.py`.
- [x] 1.4 Adicionar o parâmetro `is_producao: bool = True` na função `deploy()` e passá-lo para os passos sequenciais se necessário em `scripts/deploy_generated.py`.
- [x] 1.5 Modificar `passo_c_gerar_indice` para filtrar `compilados` de forma que apenas aqueles onde `croqui_data.get('publicar_croqui', False) == True` sejam inclusos quando `is_producao` for `True`.

## 2. Compatibilidade no Aresta Editor

- [x] 2.1 Atualizar o componente local do editor (`editor/core/croqui_experimental.py`) para invocar a função `deploy()` contendo o argumento explícito `is_producao=False`.

## 3. Script de Migração de Dados

- [x] 3.1 Criar o arquivo `scripts/migrar_publicar_croqui.py` e iterar por todas as subpastas em `database/`.
- [x] 3.2 Lidar os arquivos `croqui.yaml`, e se `revisado_manualmente == True`, inserir a chave `publicar_croqui: true` no topo ou base e sobrescrever o YAML, preservando codificação e indentação (`sort_keys=False`).
- [x] 3.4 Apagar o script de migração após seu uso, já que ele é _one-off_ (ou deixá-lo caso julgar útil historicamente, fica à escolha na execução).

## 4. Atualização de Relatórios

- [x] 4.1 Em `scripts/medir_saude_croquis.py`, criar a função `check_publicar_croqui` para ler o valor de `publicar_croqui` do YAML e checar se é `True`.
- [x] 4.2 Adicionar a nova coluna "Publicado" na saída do `STATUS_CROQUIS.md` atualizando a função `generate_report_table` e a rotina principal de coleta.
