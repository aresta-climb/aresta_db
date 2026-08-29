# Especificação: Tipagem Estática em Comandos e Controladores

## Requirements

### Requirement: Tipagem Estática Estrita em Comandos de Mutações Protobuf
O módulo `editor/commands/comandos_protobuf.py` SHALL possuir tipagem estática estrita em todas as classes de comando (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarOneof`, etc.), métodos `undo()`, `redo()`, `serializar()` e na função `deserializar_comando()`.

#### Scenario: Validação de comandos protobuf pelo MyPy
- **WHEN** o MyPy analisa `editor/commands/comandos_protobuf.py`
- **THEN** nenhuma inconsistência de tipo ou retorno ausente é reportada sob modo estrito.

### Requirement: Tipagem Estática Estrita em Comandos de Mapas e POIs
O módulo `editor/commands/comandos_mapas.py` SHALL declarar tipos estritos para manipulações de pontos de interesse, nós geométricos e transições de tela no mapa.

#### Scenario: Validação de comandos de mapas pelo MyPy
- **WHEN** o MyPy analisa `editor/commands/comandos_mapas.py`
- **THEN** todas as coordenadas e métodos de mutação são estaticamente validados sem erros.

### Requirement: Tipagem Estática Estrita em Controladores de Aplicação
Os controladores em `editor/controllers/` (`croqui_controller.py`, `mapas_controller.py`, `compilacao_controller.py`, `publish_controller.py`) SHALL possuir anotações de tipo completas em seus construtores, métodos de negócio, propriedades e sinais Qt (`Signal`).

#### Scenario: Validação de controladores pelo MyPy
- **WHEN** o MyPy analisa todos os arquivos em `editor/controllers/`
- **THEN** todas as assinaturas, retornos e interações com serviços e workers passam com 0 erros.

### Requirement: Tipagem Estática no Módulo de Build do Editor
O módulo `editor/build.py` SHALL possuir assinaturas e tipos de retorno explicitamente anotados.

#### Scenario: Validação de editor/build.py pelo MyPy
- **WHEN** o MyPy analisa `editor/build.py`
- **THEN** o arquivo é aprovado sem erros sob `strict = true`.

### Requirement: Conformidade no Teste Guardião da Onda 3
O teste `tests/tipagem_estatica_test.py` SHALL incluir os módulos de `editor/commands/` e `editor/controllers/` na lista de verificação de tipos e conformidade AST.

#### Scenario: Execução dos testes automatizados de tipagem
- **WHEN** o pytest executa `tests/tipagem_estatica_test.py`
- **THEN** todos os testes passam garantindo 100% de cobertura de tipos nos comandos e controladores.
