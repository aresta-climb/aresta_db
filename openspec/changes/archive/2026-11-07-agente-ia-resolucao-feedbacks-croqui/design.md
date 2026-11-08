# Design

## Context

Conforme descrito em `proposal.md`, o aplicativo Aresta Climb já envia feedbacks de usuários contendo metadados ricos (`croqui_id`, `Árvore de Navegação` como `Início -> Pico (id) -> Setor (nome) -> Via (nome)`, descrição textual e `screenshot.webp`), os quais a Edge Function `app-feedback` transforma em Issues públicas no repositório `aresta-climb/aresta_db` com a label `feedback:croqui`.

No `aresta_db`, os dados-fonte em `database/<croqui_id>/` são arquivos Markdown com YAML frontmatter (`setor_*.md`, `capa.md`, `mapas_gerais.md`) e `croqui.yaml`. O repositório já conta com dois workflows fundamentais:
1. [`pr-db-validator.yml`](file:///C:/Renato/Devel/aresta-climb/aresta_db/.github/workflows/pr-db-validator.yml): Valida PRs que alteram `database/**` e publica a prévia compilada.
2. [`pr-integrator.yml`](file:///C:/Renato/Devel/aresta-climb/aresta_db/.github/workflows/pr-integrator.yml): Ao receber aprovação humana (`Approve` ou comentário `/approve`), executa `scripts/deploy_generated.py` (atualizando `generated/`), faz commit assinado (`Signed-off-by`) e realiza o merge.

Portanto, o agente de IA precisa atuar exclusivamente na camada de arquivos-fonte em `database/<croqui_id>/*.{md,yaml}`, abrindo ou atualizando uma Pull Request para que a esteira existente assuma a revisão e compilação final.

## Goals / Non-Goals

**Goals:**
- Automatizar a geração e atualização de Pull Requests em `database/<croqui_id>/` a partir de Issues `feedback:croqui` e de comandos `/ai-fix` em Issues ou PRs.
- Utilizar o **Gemini 2.5 Flash** via tier gratuito do Google AI Studio (`GEMINI_API_KEY`), mantendo custo operacional zero (\$0.00) e sem consumir a cota do Cloudflare Workers AI usada no Fixalog.
- Fornecer visão espacial precisa ao modelo multimodal através da renderização em memória de uma **régua cartesiana graduada em pixels (X/Y) + grade + pontos de interesse atuais** sobre as imagens de mapa do setor.
- Minimizar o consumo de tokens de entrada através de um localizador em cascata de arquivos `.md` (Determinístico → Busca Textual Local → Desambiguação via Índice Compacto).
- Garantir segurança contra *Prompt Injection* por meio de 3 camadas: saída JSON estruturada sem execução de comandos pela IA, *Hard Jail* em Python restrito a `database/<croqui_id>/*.{md,yaml}` com validação via `pr_db_validator` (incluindo 1 autoretry), e token de GitHub App com *downscoping* no workflow YAML.

**Non-Goals:**
- Edição automática de arquivos binários compilados em `generated/` (responsabilidade exclusiva do `pr-integrator.yml` após aprovação humana).
- Desenho automático de curvas Bézier complexas de traçados vetoriais (`tracados`) ou recorte de novas fotografias.
- Alterações no aplicativo Flutter (`aresta_app`) ou nas Edge Functions do Supabase (`aresta_backend`), visto que os metadados atuais na Issue já fornecem todo o contexto necessário.

## Decisions

### 1. Motor Multimodal: Gemini 2.5 Flash (Google AI Studio Free Tier) vs. GitHub Models / Cloudflare Workers AI
- **Decisão**: Utilizar a API REST do Google AI Studio (`gemini-2.5-flash`) com Structured Outputs (`responseSchema`).
- **Racional**:
  - Os modelos gratuitos do GitHub Models não estão mais disponíveis ou possuem limites severos de tokens de entrada (8k tokens), insuficientes para enviar um arquivo `.md` de setor junto com múltiplas imagens.
  - O Cloudflare Workers AI compartilha a cota diária de 10.000 Neurons com o projeto Fixalog.
  - O tier gratuito do Google AI Studio oferece até ~250.000 tokens por minuto e centenas de requisições diárias sem exigir cartão de crédito vinculado, além de excelente capacidade nativa de visão espacial e OCR em português. Como todo o conteúdo de `aresta_db` é público sob licença `ODbL-1.0`, os termos de uso do tier gratuito do AI Studio são 100% compatíveis com o projeto.

### 2. Orquestração em GitHub Actions com Downscoping do GitHub App Token
- **Decisão**: Executar o agente dentro de um workflow GitHub Actions (`.github/workflows/ai-feedback-solver.yml`) em `aresta-climb/aresta_db`, gerando um token temporário via `actions/create-github-app-token@v3` com `BOT_CLIENT_ID` / `BOT_PRIVATE_KEY` e escopo reduzido:
  ```yaml
  permission-contents: write
  permission-pull-requests: write
  permission-issues: write
  ```
- **Racional**:
  - Repositórios públicos no GitHub possuem minutos gratuitos ilimitados no GitHub Actions.
  - Diferente do `GITHUB_TOKEN` padrão (cujas PRs não disparam outros workflows `on: pull_request`), uma PR criada com token de GitHub App dispara normalmente o `pr-db-validator.yml` e o check do DCO.
  - O *downscoping* explícito no step `create-github-app-token` garante que o token emitido para o job **não** possua `workflows: write` nem `administration: write`, impedindo qualquer modificação em `.github/workflows/**` no nível da API do GitHub.

### 3. Localização em Cascata dos Arquivos `.md` Alvo
- **Decisão**: Implementar o módulo `serving/agente_feedback/localizador_arquivos_croqui.py` operando em 3 níveis:
  ```text
  [Entrada: Corpo da Issue / Comentário / Diff da PR]
         │
         ├─▶ Nível 1 (Determinístico, 0 chamadas IA):
         │     • Se for PR: usa arquivos .md/.yaml do `git diff origin/main...HEAD`.
         │     • Se Árvore de Navegação tiver `Setor (X)` ou `Via (Y)`:
         │       cruza com `nome` dos setores e escaladas em `database/<croqui_id>/*.md`.
         │
         ├─▶ Nível 2 (Busca Textual Local, 0 chamadas IA):
         │     • Faz match normalizado (sem acentos/minúsculas) dos nomes de setores
         │       e vias de `database/<croqui_id>/` contra o texto da descrição/comentário.
         │
         └─▶ Nível 3 (Desambiguação Multimodal com Índice Compacto, 1 chamada leve IA):
               • Gera resumo textual de `database/<croqui_id>/` contendo apenas
                 `arquivo.md -> Nome do Setor -> [uid, nome, dificuldade das vias]`
                 (< 3.500 tokens mesmo no maior croqui do repositório).
               • Envia índice compacto + texto + screenshot ao Gemini Flash solicitando
                 `{"arquivos_selecionados": ["setor_x.md"]}`.
  ```
- **Racional**: Em ~85–90% dos feedbacks o usuário já está na tela do setor ou da via (ou menciona o nome no texto), permitindo resolver tudo em **uma única chamada** ao Gemini Flash enviando apenas 1 arquivo `.md` (~2k–4k tokens). Nos 10–15% restantes (ex: usuário enviou da tela do Pico e apenas circulou a via na captura de tela), o Nível 3 resolve a ambiguidade gastando menos de 4k tokens extras.

### 4. Régua Cartesiana Graduada em Memória para Mapas (`renderizador_regua_mapa.py`)
- **Decisão**: Para cada mapa referenciado no arquivo `.md` do setor selecionado (`caminho_imagem_mapa`, `largura_mapa`, `altura_mapa`), gerar em memória via `Pillow` uma imagem PNG/WebP temporária contendo:
  1. A imagem original redimensionada/mantida na proporção de `largura_mapa` x `altura_mapa`.
  2. Uma margem externa (ex: `40px`) com **régua graduada nos eixos X e Y** a cada `100px` (e marcações menores a cada `50px`) + linhas de grade tracejadas semitransparentes a cada `100px`.
  3. Desenho dos círculos atuais de `pontos_de_interesse` com seus rótulos (`'01'`, `'02'`, etc.) destacados.
- **Racional**: LLMs multimodais erram quando tentam estimar coordenadas absolutas em pixels numa imagem crua, mas têm altíssima precisão quando leem uma grade numerada explícita sobreposta à imagem. Isso permite tanto associar rabiscos do screenshot do usuário aos pontos existentes quanto corrigir/adicionar coordenadas `x`, `y` e `raio` de `pontos_de_interesse`.

### 5. Validação Local e Autoretry em Memória/Disco
- **Decisão**: Após o Gemini retornar o JSON estruturado com os arquivos modificados:
  1. O script valida o *Hard Jail* (caminho resolvido dentro de `database/<croqui_id>/`, extensão `.md` ou `.yaml`, cabeçalho SPDX presente).
  2. Executa a validação de compilação e integridade do croqui (`validar_pasta_croqui` / `pr_db_validator.py`) sobre `database/<croqui_id>`.
  3. Se a validação retornar erro (ex: `ValueError` do Protobuf por nome de enum inválido como `7c` em vez de `BR_7C`, ou referência órfã de `alvo_uid`), o orquestrador faz **1 autoretry** enviando o erro exato de validação de volta ao Gemini Flash.
- **Racional**: Garante que o bot nunca abra uma Pull Request que já nasça quebrando o CI (`pr-db-validator.yml`).

---

## Guia Passo a Passo: Configuração do Google AI Studio (Free Tier)

Este guia também será versionado em `docs/guia_configuracao_ai_studio_feedback.md` para referência contínua da equipe:

### 1. Diferença entre Google One AI Ultra e Google AI Studio
- A assinatura **Google One AI Pro / Ultra** aplica-se aos produtos de consumidor (app Gemini, Antigravity, NotebookLM) e não compartilha cota com chaves de API REST.
- Porém, o **Google AI Studio** oferece um **Free Tier ( Nível Gratuito ) independente** para qualquer conta Google, **sem necessidade de cartão de crédito** e com custo garantido de **R\$ 0,00**, suportando o modelo `gemini-2.5-flash` com folga para o volume de Issues e PRs do `aresta_db`.

### 2. Como Gerar a `GEMINI_API_KEY` Gratuita
1. Acesse [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) autenticado com a conta Google do projeto Aresta (ou sua conta pessoal).
2. Clique no botão **"Create API key"**.
3. Selecione **"Create API key in new project"** (ou escolha um projeto existente que **não** possua conta de faturamento/billing do Google Cloud vinculada).
4. Verifique na tabela de chaves se a coluna **Plan** exibe **"Free tier"**:
   - Enquanto o projeto estiver no plano *Free tier* (sem Cloud Billing anexado), é **impossível** haver qualquer cobrança financeira: caso o limite diário gratuito seja atingido, a API apenas retorna `HTTP 429 RESOURCE_EXHAUSTED` até o reset diário à meia-noite (horário do Pacífico).
5. Copie a chave gerada (começa com `AIzaSy...`).

### 3. Como Configurar no GitHub (`aresta-climb/aresta_db`)
1. No GitHub, abra o repositório `aresta-climb/aresta_db`.
2. Acesse **Settings** → **Secrets and variables** → **Actions**.
3. Clique em **"New repository secret"**:
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: Cole a chave `AIzaSy...` copiada do Google AI Studio.
4. Clique em **"Add secret"**.
   *(Os segredos `BOT_CLIENT_ID` e `BOT_PRIVATE_KEY` já existentes no repositório serão reutilizados automaticamente pelo novo workflow).*

---

## Risks / Trade-offs

- **[Risk] Tentativa de Prompt Injection no texto da Issue de um usuário anônimo** → **Mitigation**: O modelo de IA não possui ferramentas de execução de código ou shell; ele apenas retorna um objeto JSON contendo o novo texto YAML/Markdown. O script Python aplica *Hard Jail* verificando que `Path.resolve()` pertence estritamente a `database/<croqui_id>/*.{md,yaml}`, valida o schema Protobuf antes do commit e utiliza um token de GitHub App com *downscoping* sem permissão de alterar workflows nem dar merge na `main`.
- **[Risk] Indisponibilidade temporária ou limite de cota (HTTP 429) na API gratuita do Gemini** → **Mitigation**: Em caso de erro `429` ou `503`, o cliente aguarda com *backoff* curto (1 retentativa) e, caso persista, registra aviso claro no log do Actions / comentário sem quebrar o repositório, permitindo que um mantenedor dispare `/ai-fix` posteriormente.
- **[Risk] Conflito de branches ao usar `/ai-fix` repetidamente** → **Mitigation**: Para Issues, a branch segue a convenção determinística `ai-fix/issue-<numero_issue>`, sendo recriada/atualizada a partir do estado atual da PR aberta (se existir) ou da `main` (se não existir PR aberta).

## Migration Plan

1. Implementar os módulos independentes em `serving/agente_feedback/` seguindo TDD estrito (100% de cobertura comportamental e espelhamento 1:1 com `_test.py` e Fakes determinísticos `*_fake.py` + `*_fake_test.py`).
2. Adicionar o guia `docs/guia_configuracao_ai_studio_feedback.md` e atualizar a documentação do repositório.
3. Adicionar o secret `GEMINI_API_KEY` nas configurações do repositório `aresta-climb/aresta_db`.
4. Publicar o workflow `.github/workflows/ai-feedback-solver.yml`.
5. **Rollback**: Caso necessário desativar temporariamente o bot, basta desabilitar o workflow `ai-feedback-solver.yml` na aba Actions do GitHub ou remover o secret `GEMINI_API_KEY`, sem qualquer impacto nos demais workflows (`pr-db-validator.yml`, `pr-integrator.yml`, `deploy.yml`).
