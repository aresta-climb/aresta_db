# Spec Delta

## MODIFIED Requirements

### Requirement: Persistência pré-computada da malha rodoviária no modelo do Pico
O modelo `Pico` no Protobuf (`croqui.proto`) SHALL declarar `ArquivoMalhaEstrada malha_estrada = 15` (`oneof arquivo { string caminho = 1; MalhaEstradaPico conteudo = 2; }`), onde `MalhaEstradaPico` inclui `int32 versao = 4` (gravado com `VERSAO_ATUAL_MALHA_ESTRADA = 2`), persistindo no arquivo fonte `database/<id>/croqui.yaml` apenas a referência `malha_estrada: { caminho: malha_estrada.yaml }` (ou `malha_estrada_<id>.yaml` quando houver múltiplos picos), gravando o conteúdo (`latitude_referencia_e7`, `longitude_referencia_e7`, `versao` e `nos`) no arquivo YAML dedicado com cabeçalho SPDX ODbL-1.0 e expandindo `malha_estrada.conteudo` ao compilar o `compilado.binarypb`. Uma malha pré-computada SHALL ser considerada sincronizada (apta a exportar pontos para o catálogo SQLite) quando possuir ao menos um nó, coordenadas de referência idênticas a `pico.localizacao` e todos os nós com `distancia_metros > 0` possuírem `duracao_minutos > 0`, e SHALL ser considerada integralmente atualizada somente quando adicionalmente `versao >= VERSAO_ATUAL_MALHA_ESTRADA` (`2`).

#### Scenario: Serialização separada em malha_estrada.yaml e linkagem no croqui.yaml
- **WHEN** um croqui possui `pico.malha_estrada.conteudo` preenchido com pontos rodoviários e é salvo pelo Editor ou processado pelo pipeline
- **THEN** `database/<id>/croqui.yaml` armazena apenas `malha_estrada: { caminho: malha_estrada.yaml }` e os pontos (junto com `versao: 2`) são gravados em `database/<id>/malha_estrada.yaml` com cabeçalho SPDX ODbL-1.0.

#### Scenario: Hidratação em memória ao abrir no Editor e expansão no compilado.binarypb
- **WHEN** o Editor carrega `database/<id>/croqui.yaml` ou `compilar_croqui` gera `compilado.binarypb`
- **THEN** o arquivo referenciado em `malha_estrada.caminho` é lido do disco e hidratado em `pico.malha_estrada.conteudo`.

#### Scenario: Validação de sincronia entre a malha pré-computada e a localização atual do pico
- **WHEN** `pico.malha_estrada.conteudo` possui ao menos um nó, todos os nós com `distancia_metros > 0` possuem `duracao_minutos > 0`, `latitude_referencia_e7 == pico.localizacao.latitude`, `longitude_referencia_e7 == pico.localizacao.longitude` e `versao >= 2`
- **THEN** o sistema considera a malha rodoviária válida e integralmente atualizada para a localização atual do pico.

#### Scenario: Detecção de malha defasada após alteração de coordenada do pico
- **WHEN** a coordenada `pico.localizacao` é alterada para um novo par `(latitude, longitude)` diferente de `(latitude_referencia_e7, longitude_referencia_e7)`, ou existe algum nó com `distancia_metros > 0` cujo `duracao_minutos <= 0`, ou `versao < 2`
- **THEN** o sistema identifica que a malha pré-computada está desatualizada (exibindo alerta específico de versão ou ausência no card de localização do pico, no Painel de Qualidade e no deploy, mas mantendo a exportação para o catálogo caso a coordenada e `duracao_minutos` sejam válidos).
