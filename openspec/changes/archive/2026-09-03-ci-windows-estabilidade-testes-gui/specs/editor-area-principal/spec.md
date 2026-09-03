## ADDED Requirements

### Requirement: Ciclo de Vida sem Deleções Assíncronas Desnecessárias
A Janela Principal e suas páginas componentes SHALL instanciar exclusivamente os widgets necessários à sua operação, evitando a criação de elementos temporários marcados para deleção tardia (`deleteLater()`).

#### Scenario: Inicialização das páginas de conteúdo sem deleteLater
- **WHEN** a Janela Principal inicializa as páginas de dados, imagens, mapas e betas
- **THEN** cada página filha configura seu layout específico diretamente
- **AND** nenhum widget placeholder temporário é enfileirado para destruição assíncrona no loop de eventos

### Requirement: Fixture de Testes com Teardown Garantido
Os testes automatizados que instanciam a Janela Principal SHALL utilizar fixtures ou gerenciadores de contexto com teardown que garantam a invocação de `close()` e o desmonte ordenado de recursos.

#### Scenario: Teardown ordenado de janelas nos testes de interface
- **WHEN** uma função de teste de Janela Principal é executada
- **THEN** a janela é fornecida via fixture com `yield`
- **AND** ao término do teste, `janela.close()` é chamado obrigatoriamente antes do processamento final de eventos do pytest-qt