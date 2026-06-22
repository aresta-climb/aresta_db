## ADDED Requirements

### Requirement: Relatório de Validação da Migração 0002
O sistema SHALL emitir um arquivo de relatório (`ids_no_mapa_nao_encontrados.yaml`) quando o script de migração falhar ao realizar correspondência total (match exato) entre os IDs de uma escalada e os pontos de interesse de qualquer mapa no setor.

#### Scenario: IDs não encontrados nos mapas
- **WHEN** uma escalada possui `id_no_mapa` que não existe no array `pontos_de_interesse` de nenhum mapa
- **THEN** a migração remove o ID da escalada e grava a entrada no arquivo `ids_no_mapa_nao_encontrados.yaml`

#### Scenario: Match Parcial de Pontos
- **WHEN** uma escalada requer dois pontos (`["1", "A"]`) mas o mapa alvo só contém um deles (`"1"`)
- **THEN** a correspondência falha, a referência não é criada no mapa, e o grupo inteiro (`["1", "A"]`) é registrado no `ids_no_mapa_nao_encontrados.yaml`
