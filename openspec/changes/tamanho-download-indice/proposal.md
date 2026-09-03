## Why

Para permitir que aplicativos clientes (como o `aresta_app`) exibam o tamanho estimado de download de cada croqui antes que o usuário inicie o salvamento offline, o `indice.binarypb` precisa fornecer o tamanho total em bytes diretamente no resumo de cada croqui. Sem esse dado pré-computado, os clientes precisariam disparar dezenas de requisições de rede para obter o tamanho de cada imagem, gerando lentidão e consumo desnecessário de dados.

## What Changes

- **Extensão de Protobuf** (`aresta_api/proto/indice.proto`): Adiciona o campo `int64 tamanho_download_bytes = 9;` na mensagem `PrecomputadosResumoCroqui`.
- **Biblioteca Autônoma de Cálculo (Library-First)** (`scripts/calcular_tamanho_croqui_lib.py`): Cria uma biblioteca isolada, modular e sem acoplamento para calcular o tamanho total em bytes dos artefatos de download de um croqui (somando o arquivo binário `compilado.binarypb` e os arquivos de imagem válidos em `imagens/`, ignorando subdiretórios de processamento intermediário como `raw_mapas`).
- **Integração no Pipeline de Geração** (`scripts/deploy_generated.py`): Utiliza a biblioteca durante a geração do índice (`passo_c_gerar_indice`), populando o campo `resumo.precomputados.tamanho_download_bytes` no `indice.binarypb` e espelhando a informação no arquivo de depuração `indice.yaml`.
- **Bateria de Testes em Conformidade com PRINCIPIOS.md**:
  - **Testes de Integração em Primeiro Lugar**: Estabelece teste na fronteira do índice em `scripts/deploy_generated_test.py` antes da implementação interna.
  - **TDD e Co-localização**: Testes unitários escritos antes da implementação em `scripts/calcular_tamanho_croqui_lib_test.py` no mesmo diretório do módulo.
  - **100% de Cobertura Unitária**: Garantia estrita de cobertura total de código para a nova biblioteca.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability criada -->

### Modified Capabilities
- `croqui-precomputados`: Adiciona requisito de cálculo e injeção de `tamanho_download_bytes` no `PrecomputadosResumoCroqui` do `ResumoCroqui` no índice.

## Impact

- `aresta_api/proto/indice.proto` e stubs gerados (`aresta_api/proto/generated/`).
- Nova biblioteca `scripts/calcular_tamanho_croqui_lib.py` e testes `scripts/calcular_tamanho_croqui_lib_test.py`.
- Pipeline de deploy em `scripts/deploy_generated.py` e testes de integração em `scripts/deploy_generated_test.py`.
- Downstream: `aresta_app` e demais clientes externos poderão ler o tamanho consolidado diretamente do índice para apresentação de download offline.
