# Spec Delta

## MODIFIED Requirements

### Requirement: Proteção de Arquitetura Baseada em AST
O sistema SHALL incorporar uma verificação automatizada de análise estática de código (em `editor/arquitetura_mvc_test.py`) para impedir a regressão da arquitetura MVC, o uso indevido de comandos legados descontinuados e a instanciação de loggers fora da hierarquia global da aplicação, de forma análoga a padrões como ArchUnit.

#### Scenario: Violação do Contrato de Mutação
- **WHEN** qualquer arquivo fora da pasta `models/` e da pasta `commands/` tenta invocar um método mutador restrito do Model (iniciado com `_set_`)
- **THEN** a suíte de testes (`editor/arquitetura_mvc_test.py`) utilizando parsing de Árvore Sintática Abstrata (AST) SHALL falhar a etapa de build contínua e reportar o acesso ilegal.

#### Scenario: Proibição de Importação ou Uso de Comandos Legados fora da Deserialização
- **WHEN** qualquer arquivo Python em `editor/` (exceto a função `deserializar_comando` em `editor/commands/comandos_protobuf.py` e a suíte dedicada `editor/commands/comandos_legados_test.py`) importar o módulo `comandos_legados` ou referenciar/instanciar qualquer uma das 12 classes de comando legadas (`CmdAlterarPrimitivo`, `CmdRenomearEscalada`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdAdicionarMapaArquivo`, `CmdSubstituirImagemMemoria`, `CmdMigrarSetor`)
- **THEN** a suíte de testes de arquitetura (`editor/arquitetura_mvc_test.py`) utilizando inspeção de AST SHALL falhar imediatamente indicando o arquivo e a linha que violaram o isolamento dos comandos legados.

#### Scenario: Proibição de Instanciação de Loggers fora do Logger Global do Aplicativo
- **WHEN** qualquer arquivo Python de produção dentro de `editor/` (exceto `editor/core/registro_log.py`) invocar diretamente `logging.getLogger` ou instanciar `logging.Logger` em vez de usar `obter_logger` de `editor.core.registro_log`
- **THEN** a suíte de testes de arquitetura (`editor/arquitetura_mvc_test.py`) utilizando inspeção de AST SHALL falhar imediatamente reportando o arquivo e a linha da violação.
