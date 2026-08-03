## ADDED Requirements

### Requirement: Filtro de Publicação no Deploy (Produção)
O sistema SHALL filtrar croquis na geração do `indice.binarypb` (e `indice.yaml`) durante o deploy de produção baseando-se no campo `publicar_croqui`.

#### Scenario: Rodando deploy em modo de produção
- **WHEN** o deploy (`deploy_generated.py`) é invocado com a flag explícita ou padrão `--producao`
- **THEN** apenas os croquis onde `publicar_croqui` for avaliado como verdadeiro serão incluídos nos arquivos de índice resultantes.

#### Scenario: Rodando deploy em modo de desenvolvimento local (Editor)
- **WHEN** o deploy é invocado com a flag explícita `--no-producao`
- **THEN** o índice incluirá todos os croquis compilados que possuam JSON/YAML válido na base, independentemente do valor da flag `publicar_croqui`.

### Requirement: Persistência de flag de publicação no Editor Aresta
O Editor Aresta SHALL manter a integridade local permitindo a pré-visualização de croquis não publicados.

#### Scenario: Editor Aresta roda deploy para preview local
- **WHEN** o Editor Aresta (no componente `croqui_experimental.py`) realiza uma build local
- **THEN** ele passa explicitamente a configuração correspondente à flag `--no-producao` via código Python (`is_producao=False`) para garantir a inserção dos croquis no índice temporário de preview.
