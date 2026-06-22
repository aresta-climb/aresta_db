## ADDED Requirements

### Requirement: Estrutura Protobuf de Mídia
O sistema SHALL suportar mídias enriquecidas semanticamente no esquema principal de Croqui.

#### Scenario: Atualização do schema Protobuf
- **WHEN** o esquema compila uma nova versão
- **THEN** a estrutura `Escalada` MUST conter uma coleção de objetos `MidiaBeta` (com fonte, URL e thumbnail).
- **THEN** a estrutura `MidiaBeta` MUST conter opcionalmente a sub-message `MetaBeta` para armazenar o resumo de movimento extraído pelo sub-agente de IA.
