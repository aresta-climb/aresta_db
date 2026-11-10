# Spec Delta

## MODIFIED Requirements

### Requirement: Integração com croqui.proto
O sistema SHALL importar `beta.proto` em `croqui.proto` para vincular os betas aprovados diretamente na mensagem `Escalada` e a coleção de curadoria de betas no `Croqui` através do padrão `ONEOF_CONTEUDO` (`ArquivoCuradoriaBetas`), validando o contrato de serialização em `src/proto_validacao_test.py` sem manter testes legados de estruturas removidas.

#### Scenario: Importação em croqui.proto
- **WHEN** `croqui.proto` é compilado
- **THEN** ele MUST importar `beta.proto`.
- **THEN** a mensagem `Escalada` MUST conter `repeated MidiaBeta betas = 6;`, representando exclusivamente os betas aprovados que serão exportados no `compilado.binarypb`.
- **THEN** a mensagem `ArquivoCuradoriaBetas` MUST seguir o padrão `ONEOF_CONTEUDO` com `oneof arquivo { string caminho = 1; ColecaoCuradoriaBetas conteudo = 2; }` e extensão `ext_metadados_arquivo`.
- **THEN** a mensagem `Croqui` MUST conter o campo `ArquivoCuradoriaBetas curadoria_betas` persistido em arquivo YAML dedicado (`curadoria_betas.yaml`) e omitido do `compilado.binarypb` e `compilado.yaml`.

#### Scenario: Validação comportamental de serialização de Escalada.betas e FonteMidia
- **WHEN** a suíte de validação de contratos do `aresta_api` (`uv run pytest`) é executada
- **THEN** `src/proto_validacao_test.py` MUST validar a serialização *round-trip* de `Escalada.betas` populado com `MidiaBeta` contendo exclusivamente `url`, `titulo` e `fonte`, bem como o encapsulamento de `FonteMidia.Enum` com `INDEFINIDO = 0`.
- **THEN** não MUST existir arquivos de teste legados referenciando mensagens removidas (`EscaladaAlvoBusca`, `ViasExtraidasCroqui`, `CandidatosBetaPorEscalada`, `BetasPendentes`) ou campos de curadoria (`snippets`) dentro de `MidiaBeta`.
