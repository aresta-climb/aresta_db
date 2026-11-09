# Spec Delta

## MODIFIED Requirements

### Requirement: Arquivo Protobuf Dedicado de Betas
O sistema SHALL isolar as mensagens e enums relacionados a mídias e curadoria de betas no arquivo `beta.proto` em `aresta_api/proto/`, separando estritamente a estrutura publicada (`MidiaBeta`) da estrutura de avaliação e curadoria (`CandidatoMidiaBeta` e `ColecaoCuradoriaBetas`).

#### Scenario: Definição das estruturas em beta.proto
- **WHEN** o arquivo `beta.proto` é compilado
- **THEN** o enum `FonteMidia.Enum` MUST conter os valores `INDEFINIDO = 0`, `YOUTUBE = 1`, `INSTAGRAM = 2`, `BLOG = 3`, `TIKTOK = 4`, `FACEBOOK = 5`, `TWITTER = 6`, `REDDIT = 7` e `OUTRO_UGC = 8`.
- **THEN** a mensagem `MidiaBeta` MUST conter exclusivamente os campos de publicação `url` (`string`), `titulo` (`string`) e `fonte` (`FonteMidia.Enum`), sem `thumbnail_url` e sem campos de avaliação de LLM ou scraping.
- **THEN** a mensagem `CandidatoMidiaBeta` MUST conter `midia` (`MidiaBeta`), `resultado_llm` (`ResultadoLLMBeta`), `match_multiplas_fontes` (`bool`), `match_nome_no_snippet` (`bool`) e `snippets` (`repeated string`).
- **THEN** a mensagem `CuradoriaBetasEscalada` MUST indexar os betas não publicados de uma escalada através de `escalada_uid` (`string`) e conter as listas `betas_nao_scorados` (`repeated CandidatoMidiaBeta`), `betas_nao_revisados` (`repeated CandidatoMidiaBeta`) e `betas_rejeitados` (`repeated MidiaBeta`).
- **THEN** a mensagem `ColecaoCuradoriaBetas` MUST conter `repeated CuradoriaBetasEscalada escaladas = 1;`.
