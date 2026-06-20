## Why

Atualmente, os mapas conectam-se às entidades de escalada de forma fragmentada: o mapa define os Pontos de Interesse (POIs) e as escaladas contêm os campos `id_no_mapa`, `id_no_mapa_meio` e `id_no_mapa_fim`. Isso gera conflitos quando uma mesma escalada precisa aparecer em mapas diferentes (com IDs diferentes) e limita a representação de linhas a apenas 3 pontos. Além disso, impede o cross-linking direto entre mapas (ex: um botão no mapa de Setor para abrir o mapa de Grupo). A refatoração centraliza essas referências no Mapa, resolvendo o problema de acoplamento reverso.

## What Changes

- **BREAKING**: Remoção do campo `id_no_mapa` das entidades `Grupo` e `Setor`.
- **BREAKING**: Remoção dos campos `id_no_mapa`, `id_no_mapa_meio`, e `id_no_mapa_fim` de todas as variações de `Escalada` (`ViaEsportiva`, `ViaMovel`, `Boulder`, `ViaMultiplasEnfiadas`, `Highline`).
- Adição da mensagem `Referencia` no escopo de `Mapa`, contendo suporte a uma lista ilimitada de IDs (para caminhos complexos) e suporte para escopo de entidades (`grupo`, `setor`, `escalada`).
- Adição de configuração fina de câmera (`AjusteDeCamera`) para personalizar o zoom e o foco individual de referências no mapa.
- Criação de um script em Python na pasta `aresta_db/migracoes` guiado inteiramente por TDD (Test-Driven Development) garantindo 100% de test coverage para varrer os arquivos YAML do projeto e migrar todas as referências existentes do modelo antigo para o novo.

## Capabilities

### New Capabilities
- `mapa-referencias-centralizadas`: A capacidade de um Mapa referenciar entidades sem que as entidades saibam que estão sendo referenciadas, incluindo suporte a cross-linking inter-mapas e configuração fina de câmera.

### Modified Capabilities
- `protobuf-migrations`: Adicionada a exigência de documentar a política de migração em texto (`docs/`) ao realizar scripts de migração na pasta `migracoes` e o imperativo TDD em todos os scripts.

## Impact

- **Protobuf**: O arquivo `croqui.proto` será modificado radicalmente. As bindings terão que ser regeradas.
- **Camada de Dados**: Todos os YAMLs existentes ficarão inválidos até que a migração (altamente testada via TDD) seja executada.
- **Aresta UI / Gateway**: O código do gateway ou UI precisará ser atualizado para ler a apresentação do mapa a partir de `referencias` dentro do `Mapa`, e não mais dos campos `id_no_mapa*` contidos nas escaladas. (Nota: esta proposta foca na alteração do esquema de dados; o app precisará ser adaptado separadamente ou no escopo de outro PR focado em UI).
