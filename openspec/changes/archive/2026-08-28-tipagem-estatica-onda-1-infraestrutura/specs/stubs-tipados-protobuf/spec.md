# Especificação: Stubs Tipados para Protobuf

## ADDED Requirements

### Requirement: Geração Automática de Stubs .pyi no Build de Protos
O script de compilação `aresta_api/build.py` SHALL invocar o plugin `mypy-protobuf` durante o processo de geração dos códigos Protobuf para produzir arquivos de stub `.pyi` acompanhando cada arquivo `_pb2.py`.

#### Scenario: Compilação de esquemas protobuf gerando arquivos .pyi
- **WHEN** a rotina `build_protos()` em `aresta_api/build.py` for executada
- **THEN** para cada arquivo `.proto` em `aresta_api/proto/`, deve ser gerado o correspondente `.pyi` no diretório `aresta_api/proto/generated/`.

### Requirement: Autocompletação e Validação Estática de Mensagens Protobuf
Os stubs `.pyi` gerados SHALL exportar definições completas de classes de mensagem, enums, tipos de campos e métodos de serialização (`SerializeToString`, `FromString`, etc.).

#### Scenario: Verificação de acesso a atributos de mensagem protobuf pelo MyPy
- **WHEN** um código acessa um campo inexistente em uma mensagem Protobuf tipada
- **THEN** o `mypy` identifica a inconsistência estática e falha a validação com erro de atributo desconhecido.
