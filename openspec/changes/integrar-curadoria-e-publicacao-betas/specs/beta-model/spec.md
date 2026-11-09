# Spec Delta

## MODIFIED Requirements

### Requirement: Arquivo Protobuf Dedicado de Betas
O sistema SHALL isolar as mensagens e enums relacionados a mídias e curadoria de betas no arquivo `beta.proto` em `aresta_api/proto/`, separando estritamente a estrutura publicada (`MidiaBeta`) da estrutura de avaliação e curadoria (`CandidatoMidiaBeta` e `ColecaoCuradoriaBetas`).

#### Scenario: Definição das estruturas em beta.proto
- **WHEN** o arquivo `beta.proto` é compilado
- **THEN** o enum `FonteMidia.Enum` MUST conter os valores `INDEFINIDO = 0`, `YOUTUBE = 1`, `INSTAGRAM = 2` e `BLOG = 3`.
- **THEN** a mensagem `MidiaBeta` MUST conter exclusivamente os campos de publicação `url` (`string`), `titulo` (`string`) e `fonte` (`FonteMidia.Enum`), sem `thumbnail_url` e sem campos de avaliação de LLM ou scraping.
- **THEN** a mensagem `CandidatoMidiaBeta` MUST conter `midia` (`MidiaBeta`), `resultado_llm` (`ResultadoLLMBeta`), `match_multiplas_fontes` (`bool`), `match_nome_no_snippet` (`bool`) e `snippets` (`repeated string`).
- **THEN** a mensagem `CuradoriaBetasEscalada` MUST indexar os betas não publicados de uma escalada através de `escalada_uid` (`string`) e conter as listas `betas_nao_scorados` (`repeated CandidatoMidiaBeta`), `betas_nao_revisados` (`repeated CandidatoMidiaBeta`) e `betas_rejeitados` (`repeated MidiaBeta`).
- **THEN** a mensagem `ColecaoCuradoriaBetas` MUST conter `repeated CuradoriaBetasEscalada escaladas = 1;`.

### Requirement: Integração com croqui.proto
O sistema SHALL importar `beta.proto` em `croqui.proto` para vincular os betas aprovados diretamente na mensagem `Escalada` e a coleção de curadoria de betas no `Croqui` através do padrão `ONEOF_CONTEUDO` (`ArquivoCuradoriaBetas`).

#### Scenario: Importação em croqui.proto
- **WHEN** `croqui.proto` é compilado
- **THEN** ele MUST importar `beta.proto`.
- **THEN** a mensagem `Escalada` MUST conter `repeated MidiaBeta betas = 6;`, representando exclusivamente os betas aprovados que serão exportados no `compilado.binarypb`.
- **THEN** a mensagem `ArquivoCuradoriaBetas` MUST seguir o padrão `ONEOF_CONTEUDO` com `oneof arquivo { string caminho = 1; ColecaoCuradoriaBetas conteudo = 2; }` e extensão `ext_metadados_arquivo`.
- **THEN** a mensagem `Croqui` MUST conter o campo `ArquivoCuradoriaBetas curadoria_betas` persistido em arquivo Markdown dedicado (`curadoria_betas.md`) e omitido do `compilado.binarypb` e `compilado.yaml`.
