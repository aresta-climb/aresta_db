# Proposta: Onda 1 - Infraestrutura de Tipagem Estática, Stubs de Protobuf e Testes Guardiões

## Why

A natureza dinamicamente tipada do Python propicia erros em tempo de execução (`AttributeError: 'NoneType'`, `TypeError`, inconsistências em mensagens Protobuf) que causam falhas no editor e nas ferramentas do repositório. Estabelecer uma infraestrutura de tipagem estática rigorosa com verificação no `pytest` é o primeiro passo inegociável para garantir confiabilidade sistêmica e preparar o terreno para a tipagem progressiva de todo o repositório em 5 ondas.

## What Changes

- Configuração do verificador estático de tipos `mypy` em modo estrito (`strict = true`) no `pyproject.toml` com grupos de dependências `dev` via `uv`.
- Inclusão dos pacotes de stubs de tipos (`types-requests`, `types-PyYAML`, `types-protobuf`, `mypy-protobuf`).
- Integração da geração automática de arquivos `.pyi` stubs para todas as definições `.proto` em `aresta_api/build.py` utilizando o plugin `protoc-gen-mypy`.
- Criação do teste de conformidade de tipos (`tests/tipagem_estatica_test.py` ou `editor/core/tipagem_test.py`) integrado à suíte padrão do `pytest`, garantindo que qualquer violação ou módulo sem anotações quebre os testes imediatamente.
- Implementação de um metateste de inspeção sintática (AST) para validar a presença de anotações completas de parâmetros e retornos.

## Capabilities

### New Capabilities
- `infraestrutura-tipagem-estatica`: Configuração do ambiente de tipagem estrita com MyPy, pacotes de types e validação por testes automatizados no Pytest.
- `stubs-tipados-protobuf`: Geração e manutenção contínua de stubs tipados `.pyi` para todas as mensagens e enums Protobuf da `aresta_api`.

### Modified Capabilities
<!-- Nenhuma especificação comportamental existente teve seus requisitos alterados nesta fase de infraestrutura -->

## Impact

- `pyproject.toml` e `uv.lock`: Adição de `mypy`, `mypy-protobuf` e pacotes `types-*` no grupo `dev`.
- `aresta_api/build.py` e `aresta_api/proto/generated/`: Compilação de protos agora produz `.pyi` stubs acompanhando os arquivos `_pb2.py`.
- Suíte de testes: Execução do Pytest passa a validar a conformidade de tipos estáticos em tempo de teste unitário.
