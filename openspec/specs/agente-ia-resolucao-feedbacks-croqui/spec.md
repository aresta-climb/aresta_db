# agente-ia-resolucao-feedbacks-croqui Specification

## Purpose
Define o comportamento de resolução automatizada e sob demanda (`/ai-fix`) de feedbacks de croqui em Issues e Pull Requests usando visão multimodal com régua cartesiana, localização em cascata de arquivos, validação local com autoretry e isolamento estrito de escopo em `database/<croqui_id>/`.

## Requirements

### Requirement: Disparo Automático em Issues de Feedback de Croqui
O sistema MUST disparar automaticamente o fluxo de análise e proposição de correção quando uma Issue for aberta ou receber a label `feedback:croqui`, utilizando um token de GitHub App com permissões restritas por downscoping (`contents: write`, `pull-requests: write`, `issues: write`).

#### Scenario: Issue aberta com feedback acionável sobre croqui
- **WHEN** uma Issue é aberta ou rotulada com `feedback:croqui` contendo o identificador `croqui_id` e uma solicitação acionável de alteração de dados ou coordenadas de pontos de interesse
- **THEN** o sistema MUST localizar os arquivos `.md`/`.yaml` correspondentes em `database/<croqui_id>/`, gerar e validar a alteração, criar uma branch `ai-fix/issue-<numero>`, realizar um commit assinado (`Signed-off-by`) contendo `Fixes #<numero>`, abrir uma Pull Request para a branch `main` e publicar um comentário na Issue com o link da Pull Request criada

#### Scenario: Issue aberta com feedback não acionável ou ambíguo
- **WHEN** uma Issue com `feedback:croqui` solicitar edição geométrica complexa de traçados vetoriais ou não contiver informações suficientes para identificar o alvo com segurança
- **THEN** o sistema MUST abster-se de criar branch ou Pull Request e publicar um comentário explicativo na Issue orientando que um mantenedor pode responder com `/ai-fix <instruções>`

### Requirement: Disparo Sob Demanda via Comando /ai-fix em Issues e Pull Requests
O sistema MUST processar comandos `/ai-fix` publicados em comentários de Issues ou Pull Requests exclusivamente quando o autor do comentário possuir associação `OWNER`, `MEMBER` ou `COLLABORATOR` no repositório.

#### Scenario: Mantenedor comenta /ai-fix em uma Issue sem Pull Request aberta
- **WHEN** um mantenedor autorizado comenta `/ai-fix <instruções>` em uma Issue de feedback que ainda não possui Pull Request ativa na branch `ai-fix/issue-<numero>`
- **THEN** o sistema MUST combinar o contexto original da Issue com as instruções adicionais do comentário, aplicar e validar as alterações em `database/<croqui_id>/`, abrir a Pull Request correspondente e comentar o link na Issue

#### Scenario: Mantenedor comenta /ai-fix em Issue que já possui Pull Request aberta ou diretamente na Pull Request
- **WHEN** um mantenedor autorizado comenta `/ai-fix <instruções>` em uma Issue cuja branch `ai-fix/issue-<numero>` já possui Pull Request aberta, ou comenta diretamente em uma Pull Request existente que modifica `database/<croqui_id>/`
- **THEN** o sistema MUST aplicar as novas alterações sobre a branch da Pull Request existente, validar os arquivos modificados, realizar novo commit assinado (`Signed-off-by`) com push para a mesma branch e publicar um comentário confirmando a atualização da Pull Request

#### Scenario: Usuário não autorizado comenta /ai-fix
- **WHEN** um usuário sem associação `OWNER`, `MEMBER` ou `COLLABORATOR` publica um comentário contendo `/ai-fix`
- **THEN** o workflow MUST ignorar o evento sem executar chamadas ao modelo de IA nem modificar branches

### Requirement: Localização em Cascata de Arquivos do Croqui
O sistema MUST identificar quais arquivos `.md` ou `.yaml` dentro de `database/<croqui_id>/` devem ser enviados ao modelo de IA evitando carregar todos os setores do croqui desnecessariamente.

#### Scenario: Localização determinística via Árvore de Navegação ou diff da Pull Request
- **WHEN** a Issue informa `Setor (<nome_setor>)` ou `Via (<nome_via>)` na `Árvore de Navegação`, ou quando o comando `/ai-fix` é executado em uma Pull Request que já modifica arquivos em `database/<croqui_id>/`
- **THEN** o sistema MUST localizar diretamente os arquivos `.md` correspondentes em `database/<croqui_id>/` sem realizar chamada extra de desambiguação ao modelo de IA

#### Scenario: Localização via busca textual local no diretório do croqui
- **WHEN** a `Árvore de Navegação` informa apenas o Pico geral (`Pico (<croqui_id>)`), mas o texto do feedback ou do comando `/ai-fix` menciona explicitamente o nome de um setor ou escalada existente em `database/<croqui_id>/`
- **THEN** o sistema MUST selecionar localmente os arquivos `.md` que contêm o setor ou escalada correspondente

#### Scenario: Desambiguação multimodal com índice compacto do croqui
- **WHEN** os passos determinístico e de busca textual local não identificarem o arquivo `.md` (por exemplo, quando o nome da via aparece apenas na imagem de captura de tela)
- **THEN** o sistema MUST gerar um índice compacto em texto listando os arquivos `.md`, nomes de setores e nomes de escaladas de `database/<croqui_id>/` (omitindo coordenadas de mapas), consultar o modelo de IA com o índice compacto e a captura de tela para desambiguar os arquivos-alvo, e em seguida carregar apenas os arquivos `.md` selecionados

### Requirement: Renderização de Régua Cartesiana em Imagens de Mapa do Setor
O sistema MUST gerar em memória versões anotadas das imagens de mapa do setor selecionado contendo régua graduada em pixels e marcação dos pontos de interesse atuais antes de enviá-las ao modelo multimodal.

#### Scenario: Envio de mapa do setor com régua graduada e pontos de interesse
- **WHEN** um arquivo `.md` de setor selecionado possuir entradas em `mapas` com `caminho_imagem_mapa`, `largura_mapa` e `altura_mapa`
- **THEN** o sistema MUST renderizar em memória uma imagem contendo régua graduada nos eixos X (`0` a `largura_mapa`) e Y (`0` a `altura_mapa`), linhas de grade espaçadas regularmente e os círculos/rótulos de `pontos_de_interesse` atuais, enviando-a junto com a captura de tela do usuário ao modelo multimodal sem modificar o arquivo de imagem `.webp` no repositório

### Requirement: Isolamento Estrito de Escopo (Hard Jail) e Validação com Autoretry
O sistema MUST validar que toda alteração proposta pelo modelo de IA restrinja-se a arquivos `.md` ou `.yaml` dentro de `database/<croqui_id>/`, preserve cabeçalhos SPDX e passe na validação de schema/compilação antes de efetuar commit.

#### Scenario: Rejeição de alterações fora de database/<croqui_id>/ ou com extensão inválida
- **WHEN** a resposta do modelo de IA tentar criar ou modificar qualquer caminho fora de `database/<croqui_id>/` (incluindo path traversal `..`) ou arquivos cuja extensão não seja `.md` ou `.yaml`
- **THEN** o sistema MUST rejeitar imediatamente a alteração, reverter qualquer modificação em disco e abortar a criação de commit

#### Scenario: Autoretry automático quando a validação do croqui falhar na primeira tentativa
- **WHEN** a alteração proposta pelo modelo de IA nos arquivos `.md`/`.yaml` falhar na validação de schema, compilação Protobuf ou cabeçalhos SPDX do repositório
- **THEN** o sistema MUST realizar uma retentativa automática enviando a mensagem de erro exata do validador ao modelo de IA para autocorreção
- **AND** somente criar o commit e a Pull Request se a versão corrigida passar integralmente na validação

#### Scenario: Aborto seguro após falha na retentativa de validação
- **WHEN** a segunda tentativa do modelo de IA ainda produzir arquivos que falhem na validação do repositório
- **THEN** o sistema MUST descartar as alterações locais, não abrir nem atualizar a Pull Request e publicar um comentário na Issue ou Pull Request detalhando o motivo da falha de validação
