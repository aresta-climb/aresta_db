# Spec Delta

## MODIFIED Requirements

### Requirement: Atualização seletiva e incremental de croquis
O gerador do catálogo SHALL suportar modo incremental para compilações parciais ou totais, substituindo em `catalogo_croquis` e `catalogo_aresta` apenas os registros dos croquis cujos metadados de catálogo tenham efetivamente mudado, removendo croquis órfãos em compilações totais e preservando o arquivo `catalogo.db` (incluindo `atualizado_em`) sem escritas quando nenhum dado lógico do catálogo for alterado.

#### Scenario: Atualização de croqui específico
- **WHEN** o deploy é invocado passando um ou mais croquis alvos via parâmetro cujos dados de catálogo foram modificados
- **THEN** os registros anteriores dos croquis modificados são removidos de `catalogo_croquis` e `catalogo_aresta`, os novos registros são inseridos atomicamente e `versao_catalogo` é recalculada em `catalogo_meta`.

#### Scenario: Preservação de croquis inalterados
- **WHEN** um deploy parcial é executado em um banco de dados existente
- **THEN** os registros de croquis que não estavam na lista de alvos permanecem inalterados no `catalogo.db`.

#### Scenario: Imutabilidade do banco quando dados de catálogo do croqui alvo não mudam
- **WHEN** um croqui já presente no `catalogo.db` é recompilado (por exemplo, após edição exclusiva de pontos de interesse em mapas ou descrições Markdown) sem qualquer alteração nos campos de `catalogo_croquis` (`croqui_uid, id_slug, nome, cidade, estado`) ou nas linhas de `catalogo_aresta` daquele `croqui_uid`
- **THEN** o gerador não remove nem reinsere o croqui, preserva o valor anterior de `atualizado_em` na tabela `catalogo_croquis` e mantém os bytes do arquivo `catalogo.db` inalterados.

#### Scenario: Remoção de croquis órfãos em compilação completa
- **WHEN** a geração completa do catálogo (`alvos=None`) é executada sobre um `catalogo.db` existente que contém um `croqui_uid` cuja pasta compilada não existe mais no diretório `generated/`
- **THEN** os registros daquele `croqui_uid` são removidos de `catalogo_croquis` e `catalogo_aresta` e `versao_catalogo` é atualizada.

## ADDED Requirements

### Requirement: Exportação incremental determinística do catálogo em CSV
O gerador do catálogo SHALL exportar ao lado do arquivo `catalogo.db` três arquivos CSV determinísticos em UTF-8 com quebras de linha LF (`catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`) espelhando as tabelas do banco SQLite, atualizando-os apenas quando houver mudança no conteúdo do catálogo ou quando algum dos arquivos CSV estiver ausente no disco.

#### Scenario: Geração dos três arquivos CSV espelhando as tabelas do catálogo
- **WHEN** `catalogo.db` é gerado pela primeira vez ou sofre alteração em suas tabelas
- **THEN** o sistema grava no mesmo diretório do banco os arquivos `catalogo_croquis.csv` (colunas `croqui_uid,id_slug,nome,cidade,estado` ordenadas por `id_slug, croqui_uid`), `catalogo_aresta.csv` (colunas `uid,tipo,croqui_uid,nome,escalada_grau,escalada_tipo,setor_uid,grupo_uid` ordenadas por `croqui_uid, uid`) e `catalogo_meta.csv` (colunas `chave,valor` ordenadas por `chave`).

#### Scenario: Short-circuit de escrita CSV quando o catálogo não sofre alteração
- **WHEN** o gerador do catálogo é executado, nenhuma linha de `catalogo_croquis` ou `catalogo_aresta` muda e os três arquivos CSV já existem no disco
- **THEN** o sistema não reescreve `catalogo_croquis.csv`, `catalogo_aresta.csv` nem `catalogo_meta.csv`, preservando seus timestamps de modificação no sistema de arquivos.
