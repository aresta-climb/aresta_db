# Spec Delta

## MODIFIED Requirements

### Requirement: Atualização seletiva e incremental de croquis
O gerador do catálogo SHALL operar de forma 100% offline em compilações parciais ou totais, substituindo em `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada` e `catalogo_distancias_estrada` apenas os registros dos croquis modificados a partir dos artefatos `compilado.binarypb` locais (extraindo a malha rodoviária diretamente de `pico.malha_estrada` quando sincronizada com `pico.localizacao`), removendo croquis e nós órfãos e preservando `catalogo.db` sem escritas quando nenhum dado lógico mudar.

#### Scenario: População 100% offline da malha rodoviária a partir do croqui compilado
- **WHEN** `gerar_catalogo_completo` processa um `compilado.binarypb` cujo `Pico` possui `malha_estrada` sincronizada com `pico.localizacao`
- **THEN** o gerador grava os nós em `catalogo_nos_estrada` e as distâncias em `catalogo_distancias_estrada` sem realizar nenhuma requisição de rede.

#### Scenario: Descarte de malha ausente ou defasada e emissão de aviso na compilação
- **WHEN** um croqui compilado possui `Pico.localizacao` válida mas `malha_estrada` está vazia ou com coordenada de referência divergente de `Pico.localizacao`
- **THEN** `deploy_generated.py` emite um `Aviso:` não-bloqueante informando que o mapa de pontos de estrada não foi gerado para a localização do pico e `gerar_catalogo_completo` não insere distâncias defasadas em `catalogo_distancias_estrada` (acionando o fallback `Haversine * 1.3` no aplicativo).

#### Scenario: Atualização de croqui específico
- **WHEN** o deploy é invocado passando um ou mais croquis alvos via parâmetro cujos dados de catálogo ou de malha rodoviária foram modificados
- **THEN** os registros anteriores dos croquis modificados são atualizados atomicamente em `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada` e `catalogo_distancias_estrada`, e `versao_catalogo` é recalculada em `catalogo_meta`.

#### Scenario: Preservação de croquis inalterados
- **WHEN** um deploy parcial é executado em um banco de dados existente
- **THEN** os registros de croquis e distâncias rodoviárias que não estavam na lista de alvos permanecem inalterados no `catalogo.db`.

#### Scenario: Imutabilidade do banco quando dados de catálogo do croqui alvo não mudam
- **WHEN** um croqui já presente no `catalogo.db` é recompilado sem qualquer alteração nos campos de `catalogo_croquis`, nas linhas de `catalogo_aresta` ou na malha rodoviária daquele `croqui_uid`
- **THEN** o gerador não remove nem reinsere o croqui e mantém os bytes do arquivo `catalogo.db` inalterados.

#### Scenario: Remoção de croquis órfãos em compilação completa
- **WHEN** a geração completa do catálogo (`alvos=None`) é executada sobre um `catalogo.db` existente que contém um `croqui_uid` cuja pasta compilada não existe mais no diretório `generated/`
- **THEN** os registros daquele `croqui_uid` são removidos de `catalogo_croquis`, `catalogo_aresta` e `catalogo_distancias_estrada`, quaisquer `no_osm_id` em `catalogo_nos_estrada` que fiquem sem nenhuma referência em `catalogo_distancias_estrada` são expurgados, e `versao_catalogo` é atualizada.
