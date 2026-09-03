## Context

O formato `.croqui` foi concebido na fase inicial do projeto como um pacote de intercâmbio manual: uma pasta compactada em arquivo ZIP com o primeiro byte ofuscado por operação XOR com `0xFF` para descaracterizar a assinatura binária `PK`. Seu propósito original era permitir que usuários do editor desktop exportassem e importassem croquis entre computadores ou para teste manual em celulares, além de servir como artefato de teste gerado pelo fluxo de validação contínua (CI) em Pull Requests através do Cloudflare R2.

Com a conclusão da arquitetura de **Recarregamento em Tempo Real (Live Reload híbrido)** (servidor local HTTP/WebSocket no Desktop + túnel Cloudflare Worker em `previa.arestaclimb.com` + pareamento por código alfanumérico) e o fluxo integrado de submissão de Pull Requests via API do GitHub App, o arquivo físico `.croqui` tornou-se totalmente redundante. Adicionalmente, o fluxo futuro de mantenedores prevê a revisão de Pull Requests diretamente pelo editor desktop acionando o hot reload em tempo real no dispositivo móvel.

## Goals / Non-Goals

**Objetivos (Goals):**
- **Eliminação de Código Morto**: Excluir completamente a biblioteca `editor/core/croqui_format.py` (`empacotar_croqui`, `ler_croqui`, `ofuscar_primeiro_byte`) e seus testes unitários.
- **Desacoplamento do Núcleo**: Remover os métodos de exportação e importação de `.croqui` do `GerenciadorCroquiExperimental` (`editor/core/croqui_experimental.py`) e a thread de trabalho `TarefaExportacao` (`editor/core/worker.py`).
- **Limpeza de Interface Gráfica**: Remover ações e botões relacionados a `.croqui`: ação "Exportar .croqui" na barra de ferramentas superior (`area_principal.py`) e botão "Importar croqui experimental" na tela inicial (`tela_de_carregamento.py`).
- **Validação Leve e Segura no CI**: Simplificar o validador de Pull Requests (`serving/pr_db_validator.py` e `.github/workflows/pr-db-validator.yml`), mantendo validação estrita de conformidade (licenças, cabeçalhos SPDX e compilação via rotina canônica `deploy(...)`), sem gerar `.croqui` nem fazer upload para S3/R2.
- **Eliminação de Scripts Obsoletos**: Excluir o script utilitário `scripts/gerar_croqui_experimental.py` e seus testes associados.
- **Conformidade Inegociável**: Respeito estrito aos 7 princípios do documento `PRINCIPIOS.md`, incluindo 100% de cobertura de testes unitários e desenvolvimento orientado a testes (TDD).

**Fora de Escopo (Non-Goals):**
- Não remover nem alterar a estrutura de diretórios de trabalho `croquis_experimentais/<id>` (o `ExperimentalWorkspace`), que continua sendo o ambiente de rascunho local seguro para usuários do editor desktop.
- Não alterar a persistência oficial do repositório em `database/**` ou os arquivos de metadados `croqui_experimental.yaml`.
- Não alterar o serviço de submissão de Pull Requests (`PublishController`, `ServicoSubmissao`) nem o servidor de hot reload (`ServidorCelular`, `ClienteTunelRetransmissor`).

## Decisions

### Decisão 1: Exclusão Total de `croqui_format.py` sem Camada Residual
- **Decisão**: Remover integralmente o arquivo `editor/core/croqui_format.py` e seu teste `croqui_format_test.py`.
- **Alternativas consideradas**: Manter stubs com avisos de depreciação. Descartado, pois o repositório segue estritamente o princípio VI (Simplicidade e Anti-Abstração); não existem consumidores externos fora da base deste repositório.
- **Racional**: Elimina 87 linhas de código de baixo nível, ofuscação binária e dependências de leitura de streams ZIP.

### Decisão 2: Preservação do `GerenciadorCroquiExperimental` Focado em Pastas Locais
- **Decisão**: Manter a biblioteca `GerenciadorCroquiExperimental`, apenas removendo os métodos `exportar_croqui` e `importar_croqui`. As operações de criação (`_criar_estrutura_croqui`), clonagem a partir de oficial, renomeação, exclusão e compilação continuam ativas para gerenciar as pastas de rascunhos.
- **Alternativas consideradas**: Renomear ou fundir a classe. Descartado para preservar a estabilidade dos contratos com `workspace.py`, `tela_de_carregamento.py` e controladores existentes.

### Decisão 3: Validador de Pull Request como Biblioteca Pura (Library-First)
- **Decisão**: Reestruturar `serving/pr_db_validator.py` como biblioteca autossuficiente que executa:
  1. `validar_cabecalhos_e_licencas()`
  2. Compilação de teste invocando a rotina `deploy(...)` diretamente para cada pasta modificada, verificando se ocorrem exceções ou falhas.
  3. Retorno de lista de mensagens de erro sem dependência de empacotamento em disco.
- **Alternativas consideradas**: Manter geração de ZIP simples sem ofuscação. Descartado porque os revisores utilizarão checkout de branch ou o futuro painel de revisão do editor desktop integrado ao Live Reload.

### Decisão 4: Workflow de CI sem Credenciais Cloudflare R2
- **Decisão**: No arquivo `.github/workflows/pr-db-validator.yml`, eliminar os segredos de AWS/R2 (`CLOUDFLARE_S3_ACCESS_KEY_ID`, etc.), passos do AWS CLI e a criação de links de download em comentários. O bot apenas comenta o relatório textual de validação (sucesso ou erros encontrados).
- **Racional**: CI mais rápido, determinístico, seguro (sem credenciais de escrita de storage) e com custo zero de armazenamento em nuvem.

## Conformidade com os Princípios de Engenharia (PRINCIPIOS.md)

| Princípio | Aplicação nesta Mudança |
| :--- | :--- |
| **I. Tudo em Português** | Todos os novos testes, comentários, mensagens de erro, documentações e especificações são redigidos em português brasileiro estrito. |
| **II. Library-First** | `serving/pr_db_validator.py` é mantido como biblioteca pura, autossuficiente e testável de forma independente via `serving/pr_db_validator_test.py`. |
| **III. 100% de Unit Test Coverage** | Todos os módulos editados (`croqui_experimental.py`, `worker.py`, `area_principal.py`, `tela_de_carregamento.py`, `pr_db_validator.py`) terão 100% de cobertura validada via `pytest --cov`. |
| **IV. Imperativo do Teste em Primeiro Lugar (TDD)** | Para cada refatoração ou remoção, os testes são atualizados primeiro (Vermelho), o código de produção é ajustado para satisfazer a nova regra (Verde) e refatorado em seguida (Refatorar). |
| **V. Testes de Integração em Primeiro Lugar** | Os testes de integração de fronteira de carregamento e compilação são executados antes e depois das alterações nas unidades internas. |
| **VI. Simplicidade e Anti-Abstração** | Eliminação direta de código morto, sem camadas artificiais de compatibilidade para formatos obsoletos. |
| **VII. Edições via Comandos do Histórico (Undo/Redo)** | A remoção do botão de exportação não interfere na pilha de comandos do editor; nenhuma mutação de estado é feita fora de comandos `QUndoCommand`. |

## Risks / Trade-offs

- **[Risco: Usuário tentando abrir arquivo `.croqui` antigo]** → **Mitigação:** A extensão `.croqui` deixa de ser associada e os botões de importação são removidos da UI. Caso um usuário possua um arquivo `.croqui` legado e precise dos dados, basta desofuscar o primeiro byte (XOR 0xFF) e extrair com qualquer descompactador ZIP padrão.
- **[Risco: Regressão em testes existentes que referenciavam `.croqui`]** → **Mitigação:** Identificação e atualização prévia de todas as suítes de teste (`area_principal_test.py`, `tela_de_carregamento_test.py`, `croqui_experimental_test.py`, `pr_db_validator_test.py`).

## Migration Plan

1. **Fase 1 (Testes de Integração e Módulos Mortos):** Remover `workflow_export_import_test.py`, `croqui_format_test.py`, `croqui_format.py` e utilitários headless obsoletos.
2. **Fase 2 (Núcleo do Editor com TDD):** Atualizar `croqui_experimental_test.py` (Vermelho) e remover métodos de exportar/importar em `croqui_experimental.py` e `worker.py` (Verde).
3. **Fase 3 (Interface Gráfica com TDD):** Atualizar testes de views (Vermelho) e remover botões/ações em `area_principal.py` e `tela_de_carregamento.py` (Verde).
4. **Fase 4 (CI/CD e Validador com TDD):** Atualizar `pr_db_validator_test.py` (Vermelho), refatorar `pr_db_validator.py` (Verde) e simplificar o workflow do GitHub Actions.
5. **Fase 5 (Configurações e Verificação Final):** Limpar `.gitattributes`, documentações e rodar `pytest` com validação de 100% de cobertura e checagem de tipagem estrita do MyPy.
