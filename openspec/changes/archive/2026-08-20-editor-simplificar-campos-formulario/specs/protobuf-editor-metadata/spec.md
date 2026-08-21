## ADDED Requirements

### Requirement: Opções Customizadas para Booleanos Tri-State na UI
O sistema SHALL disponibilizar opções de campo (extensões do `FieldOptions`) no arquivo `croqui.proto` para personalizar os textos dos estados booleanos na interface: `booleano_texto_indefinido` (string), `booleano_texto_sim` (string) e `booleano_texto_nao` (string).

#### Scenario: Leitura de Textos Customizados de Booleano
- **WHEN** um campo booleano possui anotações `[(aresta.booleano_texto_sim) = "Possui sinal"]` e `[(aresta.booleano_texto_nao) = "Sem sinal"]`
- **THEN** a interface gráfica SHALL utilizar estes rótulos nas opções do `QComboBox` correspondente.

#### Scenario: Fallback para Textos Padrão
- **WHEN** um campo booleano não possui anotações específicas de texto booleano
- **THEN** a interface gráfica SHALL utilizar os valores padrão "Não informado", "Sim" e "Não".
