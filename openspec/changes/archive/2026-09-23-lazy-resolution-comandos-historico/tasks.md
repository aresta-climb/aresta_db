## 1. Navegação Segura e Validação de Limites em Protobuf

- [x] 1.1 Criar testes unitários em `editor/commands/comandos_protobuf_test.py` validando retorno `None` seguro em `navegar_para_mensagem` para índices de coleções repetidas fora de limites (`idx >= len`) e campos pertencentes a variantes inativas de `oneof`, e verificar falha inicial dos testes
- [x] 1.2 Implementar proteções de limites e checagem de `WhichOneof` em `navegar_para_mensagem` no arquivo `editor/commands/comandos_protobuf.py`, e verificar aprovação dos novos testes

## 2. Resolução Tardia em ComandoEditor e Subclasses Protobuf

- [x] 2.1 Criar testes unitários em `editor/commands/comandos_protobuf_test.py` cobrindo resolução tardia via `caminho_msg`, método `_obter_msg()`, registro de `logger.error` e aborto seguro quando o alvo não for encontrado no `undo()`, e deserialização de comandos sem navegação ansiosa
- [x] 2.2 Implementar método `_obter_msg()`, propriedade `msg` e construtores tolerantes aceitando `caminho_msg` nas subclasses de comando em `editor/commands/comandos_protobuf.py` (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdRenomearEscalada`), eliminando chamadas ansiosas em `deserializar()`, e verificar aprovação dos testes

## 3. Resolução Tardia em Comandos de Mapas

- [x] 3.1 Criar testes unitários em `editor/commands/comandos_mapas_test.py` validando instanciação de `CmdAdicionarMapaArquivo` via `caminho_msg`, deserialização sem navegação ansiosa e tratamento seguro de alvo inexistente
- [x] 3.2 Atualizar `CmdAdicionarMapaArquivo` em `editor/commands/comandos_mapas.py` para adotar `caminho_msg` opcional no construtor e deserialização declarativa, e verificar aprovação dos testes

## 4. Resiliência do Diário e Captura de LookupError no Histórico

- [x] 4.1 Criar testes unitários em `editor/core/historico_test.py` simulando comandos corrompidos ou com índices inexistentes gerando `IndexError`/`LookupError` durante `carregar_diario_salvo` e `restaurar_do_diario`, garantindo que não disparem erro de log inesperado
- [x] 4.2 Atualizar blocos `except` em `carregar_diario_salvo` e `restaurar_do_diario` em `editor/core/historico.py` para capturar `LookupError`, e verificar aprovação dos testes

## 5. Validação de Regressão e Cobertura

- [x] 5.1 Executar a suíte de testes de comandos e histórico (`pytest editor/commands/comandos_protobuf_test.py editor/commands/comandos_mapas_test.py editor/core/historico_test.py`) com medição de cobertura, garantindo 100% de unit test coverage e conformidade com `AGENTS.md`
