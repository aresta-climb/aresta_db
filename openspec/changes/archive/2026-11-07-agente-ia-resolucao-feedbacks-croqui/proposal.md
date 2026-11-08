# Proposal

## Why

Feedbacks sobre croquis enviados pelos usuários através do aplicativo Aresta Climb (como correções de graduação, extensão, número de proteções, conquistadores, descrições ou posição de pontos de interesse nos mapas) hoje geram GitHub Issues em `aresta-climb/aresta_db` com label `feedback:croqui`, mas exigem que um mantenedor abra manualmente o Editor Aresta ou edite os arquivos `.md`/`.yaml` do repositório para criar uma Pull Request. Automatizar a análise multimodal dessas Issues usando o modelo Gemini Flash (via tier gratuito do Google AI Studio) para propor alterações validadas diretamente em Pull Requests — além de responder a comandos `/ai-fix` de mantenedores tanto em Issues quanto em Pull Requests — reduz drasticamente o atrito operacional de curadoria comunitária mantendo custo zero de infraestrutura.

## What Changes

- **Novo workflow GitHub Actions de Resolução de Feedbacks por IA (`.github/workflows/ai-feedback-solver.yml`)**:
  - Dispara automaticamente quando uma Issue é aberta ou rotulada com `feedback:croqui` (`issues: [opened, labeled]`).
  - Dispara sob demanda quando um mantenedor autorizado (`OWNER`, `MEMBER` ou `COLLABORATOR`) comenta `/ai-fix` em uma Issue ou em uma Pull Request existente (`issue_comment: [created]`).
  - Utiliza o GitHub App existente (`BOT_CLIENT_ID` / `BOT_PRIVATE_KEY`) com **downscoping estrito de permissões** (`permission-contents: write`, `permission-pull-requests: write`, `permission-issues: write`), garantindo que o token temporário nunca possua permissão de alterar workflows (`workflows: write`) e que a criação/atualização da PR acione normalmente o `pr-db-validator.yml` e o check do DCO.
- **Localizador em Cascata de Arquivos de Setor/Croqui (`serving/agente_feedback/localizador_arquivos_croqui.py`)**:
  - **Passo 1 (Determinístico)**: Extrai `croqui_id`, `Setor (...)` e `Via (...)` da `Árvore de Navegação` da Issue (ou os arquivos `.md`/`.yaml` já alterados no `git diff` quando acionado em uma PR) para identificar o arquivo `.md` exato em milissegundos sem custo de IA.
  - **Passo 2 (Busca Textual Local)**: Caso a árvore de navegação aponte apenas para o Pico geral, faz busca textual normalizada (sem acentos/case-insensitive) do texto do feedback contra os nomes de setores e vias de `database/<croqui_id>/`.
  - **Passo 3 (Desambiguação Multimodal Leve via Gemini)**: Caso o feedback não contenha o nome no texto (ex: apenas circulou na captura de tela) ou o comando `/ai-fix` referencie outro setor, gera um **índice compacto** de `database/<croqui_id>/` (listando `arquivo.md -> nome do setor -> [vias]`, omitindo coordenadas de mapas) e faz uma chamada rápida de roteamento ao Gemini Flash (junto com o screenshot) para identificar quais arquivos `.md` devem ser carregados.
- **Renderizador de Régua Cartesiana em Mapas para Visão Multimodal (`serving/agente_feedback/renderizador_regua_mapa.py`)**:
  - Gera em memória (via `Pillow`) versões anotadas das imagens de mapa do setor (`caminho_imagem_mapa`) contendo uma moldura de **régua graduada em pixels** nos eixos X (`0` até `largura_mapa`) e Y (`0` até `altura_mapa`), grade tracejada a cada `100px` e marcação visual dos `pontos_de_interesse` atuais com seus respectivos rótulos, permitindo que o Gemini Flash cruze marcações da captura de tela do usuário e calcule coordenadas `(x, y, raio)` precisas.
- **Cliente Gemini Flash Estruturado e Fakes Determinísticos (`serving/agente_feedback/cliente_gemini_feedback.py` e `cliente_gemini_feedback_fake.py`)**:
  - Integração HTTP com a API REST do Google AI Studio (`gemini-2.5-flash`) utilizando `responseSchema` (JSON estrito) e suporte multimodal (texto + screenshot da Issue + mapas com régua).
  - Biblioteca `test-only` de Fake determinístico (`cliente_gemini_feedback_fake.py` e seu respectivo teste) para simular respostas acionáveis, não acionáveis, desambiguação e erros de validação sem rede externa nos testes.
- **Orquestrador de Aplicação Segura, Validação e Autoretry (`serving/agente_feedback/orquestrador_resolucao_feedback.py`)**:
  - **Sandbox de Escopo (Hard Jail)**: Garante que apenas arquivos `.md` e `.yaml` estritamente contidos dentro de `database/<croqui_id>/` possam ser modificados, preservando cabeçalhos `SPDX-License-Identifier: ODbL-1.0` e bloqueando qualquer tentativa de *path traversal* ou modificação fora do escopo.
  - **Validação Local e Autoretry**: Executa a validação de compilação/schema do `aresta_db` sobre as alterações propostas; se houver erro de validação (ex: enum de dificuldade inválido), realiza **1 retentativa automática (autoretry)** enviando o erro exato ao Gemini Flash para autocorreção antes de prosseguir.
  - **Criação/Atualização de Branch e Pull Request**: Cria ou atualiza a branch determinística `ai-fix/issue-<numero>` (ou a branch atual da PR quando `/ai-fix` é usado em uma PR), realiza commit assinado (`Signed-off-by`) referenciando `Fixes #<numero_issue>`, abre/atualiza a PR e comenta o resultado na Issue/PR.
- **Documentação e Guia de Configuração do Google AI Studio (`docs/guia_configuracao_ai_studio_feedback.md` e `README.md`)**:
  - Guia passo a passo detalhando como gerar a chave gratuita `GEMINI_API_KEY` no Google AI Studio (Free Tier sem cobrança), limites de cota, diferenças em relação ao Google One AI Ultra e configuração nos Secrets do GitHub.

## Capabilities

### New Capabilities
- `agente-ia-resolucao-feedbacks-croqui`: Resolução automatizada e sob demanda (`/ai-fix`) de feedbacks de croqui em Issues e Pull Requests usando visão multimodal do Gemini Flash com régua cartesiana nos mapas, localização em cascata de arquivos `.md`, validação local com autoretry, isolamento estrito de escopo em `database/<croqui_id>/` e guia de configuração do Google AI Studio.

### Modified Capabilities
<!-- Nenhuma especificação existente teve seus requisitos alterados. -->

## Impact

- **Código Novo (`aresta_db`)**:
  - `.github/workflows/ai-feedback-solver.yml`
  - `serving/agente_feedback/localizador_arquivos_croqui.py` (+ `_test.py`)
  - `serving/agente_feedback/renderizador_regua_mapa.py` (+ `_test.py`)
  - `serving/agente_feedback/cliente_gemini_feedback.py` (+ `_test.py`)
  - `serving/agente_feedback/cliente_gemini_feedback_fake.py` (+ `_test.py`)
  - `serving/agente_feedback/cliente_github_feedback.py` (+ `_test.py` e `_fake.py` / `_fake_test.py`)
  - `serving/agente_feedback/orquestrador_resolucao_feedback.py` (+ `_test.py`)
  - `serving/resolver_feedback_ia.py` (+ `_test.py`) — ponto de entrada CLI para o workflow
  - `docs/guia_configuracao_ai_studio_feedback.md`
- **Dependências**: Reutiliza `Pillow`, `PyYAML`, `protobuf` e `urllib`/`httpx` já disponíveis no ambiente `uv` do projeto.
- **Segredos de CI/CD**: Adiciona o uso de ` secrets.GEMINI_API_KEY ` no GitHub Actions e reutiliza ` secrets.BOT_CLIENT_ID ` e ` secrets.BOT_PRIVATE_KEY ` com permissões reduzidas por downscoping.
