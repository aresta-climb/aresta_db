## 1. Protobuf e Contrato de Dados

- [x] 1.1 Adicionar campo `int64 tamanho_download_bytes = 9;` em `PrecomputadosResumoCroqui` no arquivo `aresta_api/proto/indice.proto`
- [x] 1.2 Recompilar stubs Python e Dart executando `python build.py protos` (ou `python aresta_api/build.py`)

## 2. Teste de Integração na Fronteira em Primeiro Lugar (Princípio V)

- [x] 2.1 Criar teste de integração inicial em `scripts/deploy_generated_test.py` verificando a presença e exatidão de `tamanho_download_bytes` no `indice.binarypb` e `indice.yaml`, confirmando a falha inicial (Red)

## 3. Biblioteca de Cálculo de Tamanho - TDD e 100% de Cobertura (Princípios II, III, IV e VI)

- [x] 3.1 Escrever testes unitários em `scripts/calcular_tamanho_croqui_lib_test.py` cobrindo cenários com compilado e imagens, diretório de imagens ausente, arquivos inexistentes e exclusão de subdiretórios como `raw_mapas`, confirmando falha inicial (Red)
- [x] 3.2 Implementar a biblioteca isolada em `scripts/calcular_tamanho_croqui_lib.py` com a função `calcular_tamanho_croqui_bytes`, fazendo todos os testes unitários passarem (Green)
- [x] 3.3 Executar verificação de cobertura com `pytest --cov=scripts.calcular_tamanho_croqui_lib --cov-report=term-missing` e garantir 100% de cobertura unitária

## 4. Integração no Pipeline de Deploy e Validação Final

- [x] 4.1 Integrar `calcular_tamanho_croqui_bytes` no `passo_c_gerar_indice` em `scripts/deploy_generated.py`
- [x] 4.2 Adicionar a chave `tamanho_download_bytes` no dicionário de depuração exportado para `indice.yaml`
- [x] 4.3 Rodar os testes de integração em `scripts/deploy_generated_test.py` e validar que passaram para o estado verde (Green)
- [x] 4.4 Executar suite completa de testes do repositório com `python build.py test` e validar 100% de sucesso
