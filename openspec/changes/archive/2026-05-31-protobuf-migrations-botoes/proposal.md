## Why

Atualmente, qualquer alteração incompatível (breaking change) no schema do Protobuf corrompe os croquis já existentes, impedindo compilações e gerando erros no editor. A remoção recente do campo `titulo` de `ArquivoMarkdown` quebrou dezenas de croquis. Esta proposta introduz um mecanismo automatizado e sequencial de migrações locais e offline, garantindo a evolução contínua da API sem corrupção de dados dos croquis antigos.

## What Changes

- **Motor de Migração de Croquis**: Mecanismo sequencial e linear que analisa a pasta de migrações `/migracoes/` e executa scripts dinamicamente em croquis desatualizados.
- **Versionamento Sequencial**: Versionamento baseado em números inteiros sequenciais de 4 dígitos (ex: `0001`, `0002`...) para garantir uma história linear estrita.
- **Rastreabilidade**: Adição do campo `ultima_migracao` (inteiro) em `croqui.proto` e no `croqui.yaml` de cada croqui.
- **Testes Unitários por Migração**: Obrigatoriedade de arquivo `*_test.py` com o helper `scripts/helpers_migracao.py` para validar em diretórios temporários.
- **Mecanismo de Auto-cura**: Executado automaticamente ao compilar (deploy) ou ao carregar um croqui no Editor.
- **Mapeamento de Secoes Textuais para Botões (**BREAKING**)**: Primeira migração que converte a lista antiga `secoes_textuais` (ou `arquivos_markdown`) para a nova estrutura de `botoes` com o `oneof` do destino.
- **Inicialização Automática da Versão**: Configuração do ID de migração mais alto como `ultima_migracao` em novos croquis gerados no editor e no workflow do agente, evitando migrações redundantes.
- **Idempotência e Segurança**: Mecanismo de no-op nas migrações quando o croqui já foi migrado ou não possui dados obsoletos (mesmo sem tags de versão), evitando reescritas de arquivos e locks indesejados.

## Capabilities

### New Capabilities
- `protobuf-migrations`: Motor de migrações de banco de dados locais/offline baseado em scripts e números sequenciais de 4 dígitos para atualização automática de esquemas de croqui.

### Modified Capabilities
- `croqui-experimental-format`: Atualização do schema protobuf para suportar o campo `ultima_migracao` e a nova estrutura de `botoes` (removendo `secoes_textuais`).


## Impact

- `aresta_api/proto/croqui.proto`: Definição de `ultima_migracao` e a substituição de `secoes_textuais` por `botoes`.
- `scripts/preparar_submissao_lib.py`: Atualização do compilador e injetor para lidar com o novo campo de botões e executar o motor de migração.
- `editor/views/area_principal.py`: Atualização do carregamento e salvamento para migrar automaticamente ao ler e salvar.
- `editor/core/croqui_experimental.py`: Inicialização correta de `ultima_migracao` com a última versão ao criar novos croquis.
- `build.py`: Inclusão dos testes das migrações e do diretório `/tests/` na suíte do pytest.
- `.agents/workflows/converter_pdf_para_croqui.md`: Orientação explícita de inclusão de `ultima_migracao` na geração dos croquis.
- `scripts/migrador_test.py` / `scripts/helpers_migracao_test.py`: Testes unitários para garantir a estabilidade do motor e das ferramentas de teste auxiliares.
- `tests/unicidade_ids_test.py`: Validação central da unicidade de prefixos de migração no repositório.

