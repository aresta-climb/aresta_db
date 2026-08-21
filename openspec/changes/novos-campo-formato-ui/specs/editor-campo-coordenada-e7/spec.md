## ADDED Requirements

### Requirement: Biblioteca de Conversão e Parsing de Coordenadas E7
O sistema DEVE conter uma biblioteca pura em Python (`editor/core/coordenadas.py`) responsável pela conversão bidirecional entre inteiros no padrão E7 e ponto flutuante, validação de limites geográficos, formatação de hemisférios e interpretação de textos de coordenadas em múltiplos formatos.

#### Scenario: Conversão exata de ponto flutuante para E7
- **WHEN** a função de conversão recebe o valor `-19.8980280`
- **THEN** retorna o valor inteiro `-198980280`

#### Scenario: Conversão exata de E7 para ponto flutuante
- **WHEN** a função de conversão recebe o valor `-198980280`
- **THEN** retorna o valor float `-19.8980280`

#### Scenario: Interpretação de texto com par de coordenadas
- **WHEN** o parser de texto recebe a string `"-19.898028, -43.521234"`
- **THEN** identifica corretamente Latitude `-19.898028` e Longitude `-43.521234`

### Requirement: Formatação e Edição de Latitude E7 na Interface
O sistema DEVE prover um componente de interface especializado (`WidgetCampoCoordenadaE7`) para campos anotados com `CampoFormatoUi.LATITUDE_E7`, permitindo a edição em ponto flutuante com até 7 casas decimais no intervalo $[-90.0, +90.0]$ e convertendo o valor de e para inteiro no padrão E7 ($10^7$).

#### Scenario: Exibição de valor existente de latitude
- **WHEN** o formulário carrega uma mensagem com `latitude = -198980280`
- **THEN** o campo exibe o texto `-19.8980280` e um indicador visual indicando `19.8980280° S (Sul)`

#### Scenario: Edição manual de latitude via histórico
- **WHEN** o usuário altera o valor para `-20.1234567`
- **THEN** o controlador registra a alteração no modelo com o valor inteiro `-201234567` via `CmdAlterarPrimitivo`

#### Scenario: Validação de limites de latitude
- **WHEN** o usuário digita um valor fora do intervalo $[-90.0, +90.0]$ (ex: `95.0`)
- **THEN** o widget restringe ou impede a confirmação do valor inválido

### Requirement: Formatação e Edição de Longitude E7 na Interface
O sistema DEVE prover um componente de interface especializado (`WidgetCampoCoordenadaE7`) para campos anotados com `CampoFormatoUi.LONGITUDE_E7`, permitindo a edição em ponto flutuante com até 7 casas decimais no intervalo $[-180.0, +180.0]$ e convertendo o valor de e para inteiro no padrão E7 ($10^7$).

#### Scenario: Exibição de valor existente de longitude
- **WHEN** o formulário carrega uma mensagem com `longitude = -435212340`
- **THEN** o campo exibe o texto `-43.5212340` e um indicador visual indicando `43.5212340° W (Oeste)`

#### Scenario: Edição manual de longitude via histórico
- **WHEN** o usuário altera o valor para `-44.0000000`
- **THEN** o controlador registra a alteração no modelo com o valor inteiro `-440000000` via `CmdAlterarPrimitivo`

### Requirement: Colagem Inteligente de Coordenadas
O sistema DEVE detectar quando o usuário cola uma string contendo um par de coordenadas (Latitude e Longitude) e apresentar um diálogo de confirmação para aplicar os valores aos dois campos da coordenada correspondente.

#### Scenario: Colagem de par decimal simples
- **WHEN** o usuário cola a string `-19.898028, -43.521234` no campo de Latitude
- **THEN** o sistema exibe um diálogo de confirmação com Latitude `-19.898028` e Longitude `-43.521234`
- **AND WHEN** o usuário confirma
- **THEN** os campos de Latitude e Longitude da mensagem pai são atualizados para os respectivos valores inteiros E7 via histórico

#### Scenario: Inversão de coordenadas no diálogo de confirmação
- **WHEN** o diálogo de confirmação é exibido com Latitude `-43.521234` e Longitude `-19.898028`
- **AND WHEN** o usuário clica no botão de inverter coordenadas (⇄)
- **THEN** os valores são trocados para Latitude `-19.898028` e Longitude `-43.521234`

### Requirement: Atalho para Google Maps
O sistema DEVE disponibilizar um botão de ação rápida junto ao campo de coordenada para visualizar a localização geográfica no Google Maps.

#### Scenario: Abertura no Google Maps
- **WHEN** o usuário clica no botão de mapa com coordenadas válidas preenchidas
- **THEN** o sistema abre a URL do Google Maps com a latitude e longitude no navegador padrão
