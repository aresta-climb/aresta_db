# Design Técnico: Onda 1 - Infraestrutura de Tipagem Estática, Stubs de Protobuf e Testes Guardiões

## Context

O repositório Aresta Climb conta com mais de 54.000 linhas de código em Python 3.13 e possui componentes críticos de desktop (PySide6), modelos de dados (Google Protobuf) e manipuladores de banco de dados (YAML e SQLite). Para evitar erros de execução (`NoneType`, chamadas incompatíveis, quebra de contratos), foi planejado um roteiro em 5 ondas. A Onda 1 estabelece a infraestrutura técnica central: configuração de ferramentas, geração de stubs tipados para Protobuf e testes automatizados no Pytest para garantir conformidade estrita e prevenir regressões.

## Goals / Non-Goals

**Goals:**
- Configurar `mypy` no modo `--strict` no `pyproject.toml` usando `uv` como gerenciador de dependências.
- Adicionar dependências de tipagem (`mypy`, `mypy-protobuf`, `types-requests`, `types-PyYAML`, `types-protobuf`) no grupo `dev`.
- Modificar o gerador de protobufs `aresta_api/build.py` para gerar stubs `.pyi` automaticamente via plugin `protoc-gen-mypy`.
- Criar a suíte de testes de tipagem (`tests/tipagem_estatica_test.py` ou `aresta_api/core/tipagem_test.py`) com:
  - Validador MyPy programático (`mypy.api.run`).
  - Metateste de AST para assegurar que todas as novas funções contenham assinaturas e retornos tipados.
- Garantir que a Onda 1 seja validada com 100% de cobertura de testes conforme as diretrizes do repositório.

**Non-Goals:**
- Refatorar ou tipar completamente as camadas de UI do PySide6 e views nesta onda (reservado para as Ondas 3 e 4).
- Tipar todos os scripts periféricos e módulos de OCR pesados nesta fase (reservado para as Ondas 2 e 5).

## Decisions

### 1. MyPy como Verificador Estático Principal
- **Decisão**: Adotar o `mypy` com `strict = true` no `pyproject.toml`.
- **Alternativas consideradas**: `pyright` / `basedpyright`.
- **Razão**: `mypy` é o padrão de referência da comunidade Python, possui suporte nativo à execução programática em testes de unidade (`mypy.api.run`) e integração direta com o plugin `mypy-protobuf`.

### 2. Geração de Stubs de Protobuf com `mypy-protobuf`
- **Decisão**: Integrar `protoc-gen-mypy` diretamente na rotina de compilação `aresta_api/build.py`.
- **Alternativas consideradas**: Criar stubs `.pyi` manuais ou usar classes dinâmicas sem tipagem.
- **Razão**: Manuais geram risco de dessincronização quando o esquema `.proto` evolui; `mypy-protobuf` gera stubs automáticos com anotações exatas de mensagens, enums e campos repetidos.

### 3. Teste Guardião no Pytest (`tests/tipagem_estatica_test.py`)
- **Decisão**: Executar a validação de tipos diretamente como um teste de unidade dentro do `pytest`.
- **Alternativas consideradas**: Apenas verificação manual via linha de comando ou script isolado.
- **Razão**: Em conformidade com o Princípio III (100% de cobertura e testes obrigatórios), qualquer falha de tipagem ou ausência de anotações causará falha imediata na execução do `pytest` local e no CI.

## Risks / Trade-offs

- **[Risco]** `mypy` reportar erros em módulos existentes não tipados durante a transição das ondas.
  - **Mitigação**: O teste guardião da Onda 1 configurará o escopo de verificação estrita inicial para os módulos base e aplicará verificação de AST de forma progressiva e modular conforme as 5 ondas avançam.
- **[Risco]** Incompatibilidade de binário do `protoc-gen-mypy` em ambientes Windows vs Linux.
  - **Mitigação**: Invocação através do módulo Python padrão `grpc_tools.protoc` com o argumento `--mypy_out`, suportado nativamente pelo pacote `mypy-protobuf` em todas as plataformas.
