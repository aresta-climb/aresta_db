# Delta de Especificação: editor-distribuicao-linux

## ADDED Requirements

### Requirement: Configuração de Ambiente do Subsistema Gráfico e Teclado Linux
A aplicação e o pacote Flatpak DEVEM (SHALL) configurar o ambiente de execução gráfico e de teclado para suprimir avisos não-críticos de parse de tabelas Compose externas do `libxkbcommon`.

#### Scenario: Supressão de Avisos Não-Críticos do libxkbcommon
- **WHEN** a aplicação for inicializada no Linux nativamente ou sob o Flatpak
- **THEN** a variável `XKB_LOG_LEVEL` deve estar configurada como `critical` antes da inicialização do contexto gráfico do Qt
- **AND** mensagens diagnósticas sobre teclas mortas ou símbolos desconhecidos não devem poluir a saída de erro da aplicação
