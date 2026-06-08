## ADDED Requirements

### Requirement: Coordenada no ResumoCroqui
A compilação de um croqui SHALL incluir a localização (latitude e longitude) no seu respectivo `ResumoCroqui` do índice geral, para que aplicações externas possam referenciá-lo em visualizações baseadas em mapas.

#### Scenario: O croqui possui coordenadas no primeiro pico
- **WHEN** o yaml do croqui tiver um valor preenchido para `picos[0].localizacao.latitude` e `picos[0].localizacao.longitude`
- **THEN** o script `deploy_generated.py` passa esse valor intacto (já convertido no formato E7 sint32) para a mensagem protobuf `ResumoCroqui` do `indice.binarypb`

#### Scenario: O croqui não possui coordenadas em seu primeiro pico
- **WHEN** o yaml do croqui não possuir `picos[0].localizacao`
- **THEN** o script omitirá a propriedade `localizacao` na mensagem protobuf, mantendo a retrocompatibilidade e evitando apontar pro meio do oceano.
