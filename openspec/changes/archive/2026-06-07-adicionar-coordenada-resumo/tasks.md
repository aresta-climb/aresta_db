## 1. Protobuf Definitions

- [x] 1.1 Importar `croqui.proto` em `aresta_api/proto/indice.proto`
- [x] 1.2 Adicionar o campo `Coordenada localizacao = 10;` na mensagem `ResumoCroqui` do `indice.proto`
- [x] 1.3 Rodar protoc / build (ex: `python scripts/deploy_generated.py` se ele recompilar os protos) para expor as novas definições para os testes em Python.

## 2. Implementação via TDD & Test Coverage (100%)

- [x] 2.1 **[RED]** Escrever teste unitário falho para mapeamento da coordenada: no arquivo de testes (`deploy_generated_test.py`), adicionar um cenário simulando um `croqui_data` com `localizacao` e validar se o `ResumoCroqui` gerado obteve `latitude` e `longitude` corretos, e validar no dicionário yaml de debug.
- [x] 2.2 **[RED]** Escrever teste unitário falho para croqui sem localização: simular um croqui onde `picos[0]` não tenha `localizacao`, assegurando que `ResumoCroqui` não tem o campo setado (ou não ocorre falha/exception).
- [x] 2.3 **[GREEN]** Modificar `scripts/deploy_generated.py` (função `passo_c_gerar_indice`): ler `picos[0]["localizacao"]` do `croqui_data`, caso exista.
- [x] 2.4 **[GREEN]** Atribuir `latitude` e `longitude` ao campo `localizacao` do `resumo` protobuf.
- [x] 2.5 **[GREEN]** Incluir os campos de localização na geração do `item_yaml` gerado em disco para debug, apenas quando existirem.
- [x] 2.6 **[GREEN]** Rodar testes, validar que todos passaram (`pytest scripts/deploy_generated_test.py` etc).
- [x] 2.7 **[REFACTOR]** Refatorar código se necessário, garantindo limpeza, declaratividade e que a cobertura seja comprovadamente 100% sobre as novas linhas.
