# Spec Delta

## ADDED Requirements

### Requirement: Execução com Contexto Pré-Aquecido (Warm-Start) e Resolução em Turno Único ou Multi-Turno
O sistema MUST inicializar o agente de resolução de feedbacks sobre uma sessão *headless* do Editor Aresta em memória, injetando no primeiro turno um pacote *Warm-Start* (instruções/skill de uso do Editor, catálogo de skills disponíveis, índice estrutural completo de picos, grupos, setores e escaladas com seus `UID`s, subárvore detalhada do setor/escalada em foco e captura de tela do usuário) junto às ferramentas MCP do Editor e à ferramenta transacional `finalizar_resolucao`.

#### Scenario: Resolução em turno único para edições diretas com UIDs conhecidos
- **WHEN** o feedback solicita edições cujos alvos (`UID`s) já constam no pacote *Warm-Start* (como ajustar conquistadores, graduação, nome, texto ou migrar uma via para um setor já existente)
- **THEN** o modelo emite no primeiro turno as chamadas de ferramentas MCP de edição em paralelo a `finalizar_resolucao(acao="abrir_pr", ...)`, o orquestrador executa as mutações e `aresta_salvar` na sessão *headless* e, não havendo erros de compilação, conclui a resolução com apenas 1 requisição à API do modelo

#### Scenario: Resolução multi-turno sob demanda para criação de setor, leitura de skill ou renderização de mapa
- **WHEN** o feedback exige criar um novo setor antes de migrar uma escalada (como mover uma via para um setor ainda inexistente no croqui), consultar uma skill específica (`aresta_ler_skill`) ou inspecionar coordenadas visuais (`aresta_renderizar_mapa`)
- **THEN** o agente executa as ferramentas exploratórias ou preparatórias nos turnos iniciais, recebe os resultados estruturados ou blocos visuais (`UID` recém-gerado, recortes de POIs com mira `-50..+50px`) e conclui a mutação e o salvamento nos turnos seguintes dentro do limite máximo de turnos

### Requirement: Guarda Determinística de Mudança Maior, Desistência Voluntária e Circuit Breaker
O sistema MUST proteger o repositório e a cota de inferência por meio de três salvaguardas: desistência voluntária do agente (`acao="nao_acionavel"`), limite rígido de turnos (*Circuit Breaker*) e verificação determinística de impacto semântico por `UID` antes de abrir Pull Request em disparos automáticos sem `/ai-fix`.

#### Scenario: Bloqueio de Mudança Maior em Issue automática solicitando confirmação de mantenedor
- **WHEN** o evento foi disparado automaticamente pela abertura/rotulagem de uma Issue (sem comando `/ai-fix` de mantenedor) e o diff semântico entre o estado base e o estado salvo apresentar qualquer exclusão líquida de entidade (`escalada`, `setor`, `grupo`, `pico`, `mapa` ou `botao`), adição de mais de 1 setor, modificação/adição de mais de 5 escaladas, ou alteração de `id` do croqui ou `publicar_croqui`
- **THEN** o sistema MUST reverter integralmente os arquivos locais de `database/<croqui_id>/`, abster-se de abrir Pull Request e publicar um comentário na Issue descrevendo o plano de alterações proposto e solicitando confirmação de um mantenedor via `/ai-fix`

#### Scenario: Criação de até 1 setor citado e migração de escalada preservando UID liberadas automaticamente
- **WHEN** uma Issue automática solicita transferir uma escalada existente para um setor citado pelo usuário (mesmo que exija criar esse único setor novo no grupo) e ajustar seus atributos preservando o `UID` da escalada sem exclusões líquidas
- **THEN** o diff semântico classifica a operação dentro do limite seguro e o sistema abre a Pull Request normalmente

#### Scenario: Interrupção por Circuit Breaker ao atingir limite máximo de turnos
- **WHEN** o loop de ferramentas atingir o limite configurado de turnos sem concluir com `aresta_salvar` limpo de erros
- **THEN** o sistema MUST abortar novas chamadas ao modelo, restaurar o estado original de `database/<croqui_id>/` e publicar comentário na Issue ou Pull Request informando o impedimento encontrado

## MODIFIED Requirements

### Requirement: Disparo Automático em Issues de Feedback de Croqui
O sistema MUST disparar automaticamente uma única execução do fluxo de análise e proposição de correção quando uma Issue receber a label `feedback:croqui` (evitando execuções duplicadas simultâneas de abertura + rotulagem por meio de filtro de evento e controle de `concurrency` por número do alvo), utilizando um token de GitHub App com permissões restritas por downscoping (`contents: write`, `pull-requests: write`, `issues: write`).

#### Scenario: Issue aberta com feedback acionável sobre croqui
- **WHEN** uma Issue é rotulada com `feedback:croqui` contendo o identificador `croqui_id` e uma solicitação acionável dentro do limite seguro de impacto
- **THEN** o sistema MUST executar uma única instância do workflow, aplicar e compilar a alteração via Editor Headless em `database/<croqui_id>/`, criar uma branch `ai-fix/issue-<numero>`, realizar um commit assinado (`Signed-off-by`) contendo `Fixes #<numero>`, abrir uma Pull Request para a branch `main` e publicar um único comentário na Issue com o link da Pull Request criada

#### Scenario: Issue aberta com feedback não acionável ou ambíguo
- **WHEN** uma Issue com `feedback:croqui` solicitar edição geométrica complexa de traçados vetoriais do zero, referir-se a falha do aplicativo móvel ou não contiver informações suficientes para edição segura (mesmo após inspeção na sessão *headless*)
- **THEN** o agente invoca `finalizar_resolucao(acao="nao_acionavel", ...)`, o sistema restaura `database/<croqui_id>/`, abstém-se de criar branch ou Pull Request e publica um comentário explicativo na Issue orientando que um mantenedor pode responder com `/ai-fix <instruções>`

### Requirement: Disparo Sob Demanda via Comando /ai-fix em Issues e Pull Requests
O sistema MUST processar comandos `/ai-fix` publicados em comentários de Issues ou Pull Requests exclusivamente quando o autor do comentário possuir associação `OWNER`, `MEMBER` ou `COLLABORATOR` no repositório, tratando o comando do mantenedor como autorização explícita inclusive para Mudanças Maiores.

#### Scenario: Mantenedor comenta /ai-fix em uma Issue sem Pull Request aberta
- **WHEN** um mantenedor autorizado comenta `/ai-fix <instruções>` em uma Issue de feedback que ainda não possui Pull Request ativa na branch `ai-fix/issue-<numero>`
- **THEN** o sistema MUST combinar o contexto original da Issue com as instruções do comentário (dispensando a trava de Mudança Maior), aplicar e compilar as alterações via Editor Headless em `database/<croqui_id>/`, abrir a Pull Request correspondente e comentar o link na Issue

#### Scenario: Mantenedor comenta /ai-fix em Issue que já possui Pull Request aberta ou diretamente na Pull Request
- **WHEN** um mantenedor autorizado comenta `/ai-fix <instruções>` em uma Issue cuja branch `ai-fix/issue-<numero>` já possui Pull Request aberta, ou comenta diretamente em uma Pull Request existente que modifica `database/<croqui_id>/`
- **THEN** o sistema MUST aplicar as novas alterações sobre a branch da Pull Request existente via Editor Headless, validar a compilação, realizar novo commit assinado (`Signed-off-by`) com push para a mesma branch e publicar um comentário confirmando a atualização da Pull Request

#### Scenario: Usuário não autorizado comenta /ai-fix
- **WHEN** um usuário sem associação `OWNER`, `MEMBER` ou `COLLABORATOR` publica um comentário contendo `/ai-fix`
- **THEN** o workflow MUST ignorar o evento sem executar chamadas ao modelo de IA nem modificar branches

### Requirement: Isolamento Estrito de Escopo (Hard Jail) e Validação com Autoretry
O sistema MUST garantir que toda modificação persistida em disco restrinja-se exclusivamente a arquivos válidos dentro de `database/<croqui_id>/` (incluindo criação, atualização e remoção de arquivos `.md`/`.yaml` gerenciadas pelo Editor Headless), preserve cabeçalhos SPDX `ODbL-1.0` e passe sem erros na compilação oficial antes de efetuar commit.

#### Scenario: Rejeição de alterações fora de database/<croqui_id>/ ou com extensão inválida
- **WHEN** após a execução da sessão houver qualquer arquivo modificado ou criado fora de `database/<croqui_id>/`, arquivo com extensão inválida na raiz do croqui ou frontmatter YAML sem cabeçalho SPDX `ODbL-1.0` / `Copyright (C)`
- **THEN** o sistema MUST rejeitar imediatamente a alteração, restaurar integralmente o estado Git de trabalho e abortar a criação de commit

#### Scenario: Autoretry automático quando a validação do croqui falhar na primeira tentativa
- **WHEN** o agente tentar finalizar a resolução e `aresta_salvar` reportar erros do compilador do Editor ou violação de cabeçalho SPDX na tentativa inicial
- **THEN** o orquestrador MUST devolver as mensagens exatas do compilador como resposta de ferramenta ao modelo de IA no turno seguinte (enquanto houver orçamento em `max_turnos`) para autocorreção
- **AND** somente criar o commit e a Pull Request se o salvamento subsequente passar integralmente na validação

#### Scenario: Aborto seguro após falha na retentativa de validação
- **WHEN** os turnos disponíveis de retentativa se encerrarem e o croqui continuar apresentando erro de compilação ou validação de escopo
- **THEN** o sistema MUST restaurar integralmente `database/<croqui_id>/`, não abrir nem atualizar a Pull Request e publicar um comentário na Issue ou Pull Request detalhando o erro encontrado

## REMOVED Requirements

### Requirement: Localização em Cascata de Arquivos do Croqui
**Reason**: Substituído pelo carregamento integral do croqui em memória no Editor Headless combinado ao pacote *Warm-Start* com índice de `UID`s de todos os setores/escaladas e introspecção sob demanda via `aresta_obter_arvore`.
**Migration**: Utilizar o gerador de contexto *Warm-Start* sobre `CroquiModel` e as ferramentas `aresta_obter_arvore` e `aresta_listar_escaladas` da sessão *headless*.

### Requirement: Renderização de Régua Cartesiana em Imagens de Mapa do Setor
**Reason**: Substituído pela ferramenta nativa `aresta_renderizar_mapa` do Editor Headless, que renderiza grade métrica e recortes ampliados de POIs (`-50px` a `+50px`) apenas sob demanda quando o feedback envolve mapas, eliminando gasto desnecessário de tokens de imagem em feedbacks textuais.
**Migration**: Invocar `aresta_renderizar_mapa` diretamente através do catálogo MCP da `SessaoEditorHeadless`.
