# Guia de Configuração: Agente de IA para Resolução de Feedbacks (Google AI Studio)

Este documento descreve como configurar a chave gratuita `GEMINI_API_KEY` do **Google AI Studio (Free Tier)** para o workflow automatizado [`.github/workflows/ai-feedback-solver.yml`](../.github/workflows/ai-feedback-solver.yml) e como utilizar o agente em Issues e Pull Requests do `aresta_db`.

---

## 1. Sobre Costos e a Assinatura do Google One AI Ultra

- **Google One AI Pro / Ultra vs. API do Google AI Studio**: A assinatura consumidor do Google One AI Pro / Ultra aplica-se aos aplicativos voltados ao usuário final (Gemini Web/App, Antigravity, NotebookLM, Workspace), mas **não compartilha cota com chaves de API REST**.
- **Tier Gratuito (Free Tier) Independente e Custo Zero**: Qualquer conta Google possui acesso ao **Free Tier** do Google AI Studio para os modelos **`gemini-3.8-flash`** (usado na geração da proposta e leitura espacial da régua nos mapas) e **`gemini-3.5-flash-lite`** (usado na etapa rápida de desambiguação de arquivos quando necessário), **sem necessidade de cadastrar cartão de crédito**. Como cada modelo tem sua própria cota diária independente no Free Tier, dividir a desambiguação no `3.5-flash-lite` e a proposta principal no `3.8-flash` preserva a cota do modelo principal.
- **Atenção ao Modo Pago (Paid Tier)**: No Google AI Studio, caso você vincule uma conta de faturamento (*Cloud Billing*) ao projeto para mudá-lo para *Paid tier*, **não há franquia gratuita** (a cobrança passa a ocorrer desde o 1º token). Portanto, para manter custo R\$ 0,00 garantido, crie a chave em um **projeto separado sem conta de faturamento vinculada**.
- **Compatibilidade de Licença**: No Free Tier do AI Studio, entradas e saídas não são faturadas e podem ser processadas pelo Google conforme os termos públicos do serviço — o que é 100% compatível com o `aresta_db`, visto que todo o nosso catálogo e as Issues de croqui já são públicos sob licença aberta `ODbL-1.0`.

---

## 2. Passo a Passo: Como Criar a `GEMINI_API_KEY` Gratuita

1. Acesse [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) logado na conta Google do projeto Aresta (ou na sua conta Google).
2. Clique no botão **"Create API key"**.
3. Escolha **"Create API key in new project"** (ou selecione um projeto que **não** possua conta de faturamento *Cloud Billing* vinculada).
4. Confira na listagem de chaves se a coluna **Plan** mostra **"Free tier"**:
   - Enquanto o projeto exibir **Free tier** (sem faturamento vinculado), **é impossível haver cobrança**. Caso o limite diário gratuito (~250 a 500 requisições/dia) seja alcançado, a API simplesmente responde `HTTP 429 RESOURCE_EXHAUSTED` até a virada do dia (meia-noite no horário do Pacífico).
5. Copie a chave gerada (formato `AIzaSy...`).

---

## 3. Passo a Passo: Como Configurar o Secret no GitHub

1. Abra o repositório `aresta-climb/aresta_db` no GitHub.
2. Navegue até **Settings** → **Secrets and variables** → **Actions**.
3. Clique em **"New repository secret"**:
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: Cole a chave `AIzaSy...` gerada no passo anterior.
4. Clique em **"Add secret"**.

> **Nota sobre o GitHub App Token**: O workflow reutiliza automaticamente os segredos `BOT_CLIENT_ID` e `BOT_PRIVATE_KEY` já configurados no repositório, aplicando **downscoping estrito** (`permission-contents: write`, `permission-pull-requests: write`, `permission-issues: write`).

---

## 4. Como Usar o Agente no Dia a Dia

### A. Disparo Automático na Abertura de Issue (`feedback:croqui`)
Sempre que um usuário envia um feedback sobre um croqui pelo app Aresta Climb:
1. A Edge Function `app-feedback` cria uma Issue com a label `feedback:croqui`.
2. O workflow `Resolvedor de Feedbacks por IA (Gemini Flash)` inicia automaticamente:
   - Localiza o arquivo `.md` correspondente em `database/<croqui_id>/` (via Árvore de Navegação, busca textual local ou desambiguação multimodal com índice compacto).
   - Renderiza em memória os mapas do setor com **régua cartesiana graduada em pixels (X/Y) + pontos de interesse atuais** e envia junto com a captura de tela do usuário ao Gemini Flash.
   - Valida a alteração localmente contra o compilador Protobuf (`deploy_generated.py`) com até **1 retentativa automática (autoretry)** se houver erro de schema.
   - Abre uma Pull Request na branch `ai-fix/issue-<numero>` (com `Fixes #<numero>`) e comenta o link na Issue!
3. Para aprovar e publicar a PR, basta revisar o diff e comentar `/approve` (ou aprovar pelo GitHub Review) na PR — o `pr-integrator.yml` compila o `generated/` e faz o merge automaticamente.

### B. Comando `/ai-fix` Sob Demanda (em Issues ou Pull Requests)
Qualquer mantenedor (`OWNER`, `MEMBER` ou `COLLABORATOR`) pode comentar `/ai-fix <instruções>` tanto em uma **Issue** quanto diretamente em uma **Pull Request**:
- **Em uma Issue onde o bot teve dúvida**:
  ```text
  /ai-fix A via que o usuário circulou é a Excalibur no Setor Bem-vindo, muda o grau para 7b
  ```
- **Em uma Pull Request já aberta (criada pela IA ou pelo Editor Aresta)**:
  ```text
  /ai-fix Aproveita e altera a extensão da via Excalibur para 40m e adiciona 12 proteções
  ```
  O agente aplica a mudança diretamente sobre a branch da PR existente, valida o schema e faz um novo commit assinado (`Signed-off-by`) atualizando a PR!
