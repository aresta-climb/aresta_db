# Spec Delta

## Purpose

Garante que o roteador de alertas operacionais (`aresta-alertas-worker`) evite abrir Issues duplicadas no GitHub quando já existir uma Issue aberta com o mesmo título no mesmo repositório, registrando os detalhes completos de novas ocorrências como comentário na Issue existente e informando as etapas (`steps`) que falharam em todas as falhas de `workflow_run`.

## ADDED Requirements

### Requirement: Deduplicação de Issues Abertas com Registro de Comentário
O sistema SHALL verificar se já existe uma Issue aberta (excluindo Pull Requests) com exatamente o mesmo título no repositório destino antes de criar uma nova Issue de alerta ou emergência no GitHub. Caso exista, o sistema MUST adicionar um comentário na Issue aberta contendo o corpo completo da nova ocorrência e retornar o número e a URL da Issue existente sem criar uma Issue duplicada, mantendo a Issue aberta até fechamento manual mesmo que execuções posteriores tenham sucesso.

#### Scenario: Primeira falha abre nova Issue no GitHub
- **WHEN** o roteador de alertas processa uma falha de CI/CD, deploy ou alerta do Sentry e não existe nenhuma Issue aberta no repositório destino com o mesmo título
- **THEN** o sistema MUST criar uma nova Issue no repositório com o título, corpo e labels configurados
- **THEN** o sistema MUST despachar a notificação para os canais configurados (Discord, `ntfy`, WAHA) incluindo o link e o número da nova Issue criada.

#### Scenario: Falha subsequente com Issue aberta adiciona comentário na Issue existente
- **WHEN** o roteador de alertas processa uma nova falha ou alerta cujo título coincide exatamente com uma Issue já aberta no mesmo repositório
- **THEN** o sistema MUST NÃO criar uma segunda Issue no GitHub
- **THEN** o sistema MUST publicar um comentário na Issue aberta existente contendo o cabeçalho `### 🔄 Nova Ocorrência Detectada` seguido de todos os detalhes da nova ocorrência (repositório, workflow/serviço, etapas com erro, commit, autor e URL dos logs da nova execução)
- **THEN** o sistema MUST despachar a notificação para os canais configurados referenciando a URL e o número da Issue existente.

#### Scenario: Sucesso subsequente de workflow não fecha a Issue aberta automaticamente
- **WHEN** um `workflow_run` termina com `conclusion === "success"` na branch `main` após uma falha anterior
- **THEN** o sistema MUST ignorar o evento sem fechar automaticamente a Issue aberta, preservando-a para inspeção humana de causas intermitentes (*flaky*) ou pontuais.

### Requirement: Identificação das Etapas Falhas em Workflows de Produção
O sistema SHALL consultar as etapas (`steps`) que falharam na execução do GitHub Actions (`workflow_run`) também para falhas na branch de produção (`main`, `master` ou tags `v*`) e no workflow de deploy do `aresta_db`, incluindo a linha `Etapa(s) com Erro` tanto na notificação enviada aos canais quanto no corpo da Issue ou comentário no GitHub.

#### Scenario: Falha de workflow na branch main inclui etapas com erro
- **WHEN** um evento `workflow_run` com `conclusion` de falha na branch `main` é recebido pelo roteador de alertas
- **THEN** o sistema MUST consultar os jobs da execução na API do GitHub para extrair os nomes dos `steps` que falharam
- **THEN** o texto do alerta e o corpo da Issue (ou comentário de nova ocorrência) MUST incluir o campo `Etapa(s) com Erro` listando as etapas que falharam (ou o `conclusion` da execução caso nenhuma etapa individual seja retornada).
