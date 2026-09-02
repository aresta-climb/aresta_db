## Context

O formato `.croqui` foi concebido na fase inicial do projeto como um pacote de intercâmbio manual: uma pasta compactada em ZIP com o primeiro byte ofuscado por XOR `0xFF` para descaracterizar a assinatura `PK`. Seu propósito era permitir que usuários do editor desktop exportassem e importassem croquis entre computadores ou para teste manual em celulares, além de servir como artefato de teste gerado pelo CI em Pull Requests via Cloudflare R2.

Com a conclusão da arquitetura de **Live Reload híbrido** (servidor local HTTP/WebSocket no Desktop + túnel Cloudflare Worker em `previa.arestaclimb.com` + pareamento por código alfanumérico) e o fluxo integrado de submissão de Pull Requests via GitHub API / App, o arquivo físico `.croqui` tornou-se totalmente redundante. Adicionalmente, o fluxo futuro de mantenedores prevê a revisão de Pull Requests diretamente pelo editor desktop acionando o hot reload em tempo real no dispositivo móvel.

## Goals / Non-Goals

**Goals:**
- Eliminar completamente a biblioteca `editor/core/croqui_format.py` (`empacotar_croqui`, `ler_croqui`, `ofuscar_primeiro_byte`) e seus testes unitários.
- Remover os métodos de exportação e importação de `.croqui` do `GerenciadorCroquiExperimental` (`editor/core/croqui_experimental.py`) e a thread `TarefaExportacao` (`editor/core/worker.py`).
- Remover as ações de UI relacionadas a `.croqui`: botão "Exportar .croqui" na barra de ferramentas superior (`area_principal.py`) e botão "Importar croqui experimental" na tela inicial (`tela_de_carregamento.py`).
- Simplificar o validador de Pull Requests (`serving/pr_db_validator.py` e `.github/workflows/pr-db-validator.yml`), mantendo validação estrita de conformidade (licenças, cabeçalhos SPDX e compilação via `deploy(...)`), sem gerar `.croqui` nem fazer upload para S3/R2.
- Excluir o script utilitário `scripts/gerar_croqui_experimental.py` e seus testes associados.
- Manter 100% de cobertura de testes unitários e respeito integral a todos os princípios do `PRINCIPIOS.md`.

**Non-Goals:**
- Não remover nem alterar a estrutura de diretórios de trabalho `croquis_experimentais/<id>` (o `ExperimentalWorkspace`), que continua sendo o ambiente de rascunho local seguro para usuários do editor desktop.
- Não alterar a persistência oficial do repositório em `database/**` ou os arquivos de metadados `croqui_experimental.yaml`.
- Não alterar o serviço de submissão de PRs (`PublishController`, `ServicoSubmissao`) nem o servidor de hot reload (`ServidorCelular`, `ClienteTunelRetransmissor`).

## Decisions

### Decisão 1: Exclusão Total de `croqui_format.py` sem Camada de Compatibilidade
- **Decisão:** Remover integralmente o arquivo `editor/core/croqui_format.py` e seu teste `croqui_format_test.py`.
- **Alternativas consideradas:** Manter stubs ou aviso de depreciação. Descartado, pois o repositório segue o princípio de Simplicidade e Anti-Abstração (PRINCIPIOS.md VI); não há consumidores externos fora deste ecossistema.
- **Impacto:** Menos 87 linhas de código legado e testes associados.

### Decisão 2: Preservação do `GerenciadorCroquiExperimental` Focado em Pastas Locais
- **Decisão:** Manter a classe `GerenciadorCroquiExperimental`, apenas removendo os métodos `exportar_croqui` e `importar_croqui`. As operações de criação (`_criar_estrutura_croqui`), clonagem a partir de oficial, renomeação, exclusão e compilação continuam ativas para gerenciar as pastas de rascunhos.
- **Alternativas consideradas:** Renomear ou fundir a classe. Descartado para manter estabilidade nas chamadas do `workspace.py`, `tela_de_carregamento.py` e controladores existentes.

### Decisão 3: Validador de PR Headless Focado em Verificação Limpa
- **Decisão:** Reestruturar `serving/pr_db_validator.py` para executar:
  1. `validar_cabecalhos_e_licencas()`
  2. Compilação de teste invocando `deploy(...)` diretamente em um diretório temporário para cada pasta modificada, verificando se há exceções ou falhas.
  3. Não gerar nenhum arquivo `.croqui` nem empacotar nada.
- **Alternativas consideradas:** Manter um empacotamento ZIP simples. Descartado porque os revisores utilizarão checkout de branch ou o futuro painel de revisão do editor desktop integrado ao Live Reload.

### Decisão 4: Workflow CI sem Credenciais Cloudflare R2
- **Decisão:** No `.github/workflows/pr-db-validator.yml`, eliminar os segredos de AWS/R2 (`CLOUDFLARE_S3_ACCESS_KEY_ID`, etc.), passos do AWS CLI e a criação de links de download em comentários. O bot apenas comenta o status da validação (sucesso ou erros encontrados).
- **Impacto:** CI muito mais rápido, seguro (menos superfícies de vazamento de credenciais) e sem custos de armazenamento.

## Risks / Trade-offs

- **[Risco: Usuário tentando abrir arquivo `.croqui` antigo]** → **Mitigação:** A extensão `.croqui` deixa de ser registrada no SO e os botões de importação são removidos da UI. Caso um usuário possua um `.croqui` antigo e precise dos dados, basta desofuscar o primeiro byte (XOR 0xFF) e extrair com qualquer descompactador ZIP padrão.
- **[Risco: Quebra em testes existentes que usavam fixtures `.croqui`]** → **Mitigação:** Atualizar `area_principal_test.py`, `tela_de_carregamento_test.py`, `croqui_experimental_test.py` e remover testes legados (`workflow_export_import_test.py`, `gerar_croqui_experimental_test.py`, `test_integracao_gerar_croqui.py`).

## Migration Plan

1. **Remoção de Arquivos Mortos:** Excluir `croqui_format.py`, `scripts/gerar_croqui_experimental.py` e seus respectivos testes.
2. **Refatoração do Core & Workers:** Limpar `croqui_experimental.py` e `worker.py`.
3. **Refatoração de Views & Controladores:** Atualizar `area_principal.py` e `tela_de_carregamento.py`.
4. **Refatoração do CI & Serving:** Atualizar `pr_db_validator.py` e `pr-db-validator.yml`.
5. **Configurações:** Atualizar `.gitattributes` e documentação.
6. **Verificação de Testes:** Executar `pytest` para garantir 100% de aprovação e integridade de cobertura.
