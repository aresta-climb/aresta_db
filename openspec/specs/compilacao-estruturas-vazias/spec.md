## Purpose

Garante o suporte à compilação e depuração de croquis contendo picos, grupos ou setores incompletos ou em progresso, além de manter resiliência a nulos no gerador markdown.

## Requirements

### Requirement: Compilação de Picos, Grupos e Setores Vazios ou Incompletos
O pipeline de compilação e validação do croqui (`compilar_croqui`, `expandir_arquivo_generico`, `injetar_precomputados`) SHALL permitir e processar com sucesso croquis contendo Picos sem setores, Grupos sem setores e Setores sem vias, tratando coleções vazias como estados válidos de edição em progresso.

#### Scenario: Compilação de Pico recém-criado sem setores
- **WHEN** o croqui contém um Pico sem elementos em `setores_ou_grupos` (lista vazia)
- **THEN** o pipeline de compilação SHALL gerar o `compilado.binarypb` e `compilado.yaml` sem erros, calculando `precomputados` com totais zerados para o pico.

#### Scenario: Compilação de Grupo recém-criado sem setores filhos
- **WHEN** o croqui contém uma referência para um Grupo (`grupo`) cujo arquivo ou nó possui a lista `setores` vazia ou não informada
- **THEN** a rotina `expandir_arquivo_generico` SHALL preservar o tipo como `grupo`, preencher `setores: []` e não rebaixar a estrutura para `setor`.

#### Scenario: Compilação de Setor recém-criado sem vias cadastradas
- **WHEN** o croqui contém um Setor com lista de `escaladas` vazia
- **THEN** o pipeline de compilação SHALL compilar com sucesso, calculando `total_escaladas: 0` nos pré-computados sem disparar exceções de ausência de vias.

### Requirement: Resiliência a Nulos na Geração de Compilado Markdown
A rotina de geração de documentação de depuração (`gerar_compilado_md`) SHALL manipular defensivamente objetos nulos (`None`) ou tipos vazios ao cruzar as estruturas originais de `croqui.yaml` com as estruturas expandidas de `compilado.yaml`.

#### Scenario: Geração de compilado.md com grupo ou setor vazio
- **WHEN** a função `gerar_compilado_md` processa um grupo ou setor cujo conteúdo compilado correspondente é nulo (`None`) ou possui dicionário vazio
- **THEN** a rotina não SHALL disparar `AttributeError: 'NoneType' object has no attribute 'get'`, renderizando a respectiva seção com conteúdo seguro ou lista vazia no arquivo markdown de saída.
