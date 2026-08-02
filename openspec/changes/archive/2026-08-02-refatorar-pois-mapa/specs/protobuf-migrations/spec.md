## ADDED Requirements

### Requirement: Migração de POIs Retangulares em Mapas
O sistema SHALL fornecer um script de migração para atualizar instâncias antigas da chave `"box"` nos arquivos JSON de mapas para a nova chave `"retangulo"`.

#### Scenario: Conversão de box para retangulo no JSON raw
- **WHEN** o script de migração processa um diretório de arquivos JSON (ex: `raw_mapas/`)
- **THEN** o script SHALL identificar qualquer objeto de ponto de interesse contendo a chave `"box"` e renomear essa chave para `"retangulo"`
- **AND** o script SHALL manter todos os valores internos inalterados.
