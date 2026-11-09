---
description: Pipeline integrado de descoberta multi-fonte (YouTube, Instagram e Blogs), avaliação via MCP por sub-agentes e curadoria 1 a 1 no Editor Aresta
---

# Workflow: Coleta e Curadoria de Betas de Escalada

Este workflow descreve o ciclo integrado entre o **Editor Aresta** e o agente conectado via MCP para descoberta, pontuação por IA e publicação limpa de links de beta em `Escalada.betas`.

---

## 1. Coleta Multi-Fonte no Editor Aresta (`betas_nao_scorados`)

1. No **Editor Aresta**, abra o croqui desejado e acesse a aba **Betas** na barra lateral (ou clique em **"🔍 Abrir na Revisão de Betas"** dentro da ficha de uma `Escalada` na aba **Dados**).
2. Clique em **"🌐 Coletar Betas..."** para abrir o Wizard de coleta:
   - Selecione as escaladas desejadas e inicie a coleta.
   - Os extratores (`ExtratorYouTube`, `ExtratorDuckDuckGo`, `ExtratorVertexSearch` e `ExtratorBlog`) buscam vídeos, reels/posts do Instagram e relatos em páginas de blog (`FonteMidia.BLOG`), ignorando automaticamente qualquer URL já presente nas 4 listas da escalada (`betas`, `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados`).
   - Os novos candidatos são inseridos em `curadoria_betas.conteudo.escaladas` na lista `betas_nao_scorados` via comando reversível (`Undo`/`Redo`).

---

## 2. Avaliação Semântica via MCP (`avaliar_betas_croqui`)

1. Com candidatos presentes na seção **2. Betas Não Scorados**, acione a skill [avaliar_betas_croqui](file:///c:/Renato/Devel/aresta-climb/aresta_db/.agents/skills/avaliar_betas_croqui/SKILL.md):
   > *"Execute a skill `avaliar_betas_croqui` para avaliar e pontuar os `betas_nao_scorados` deste croqui."*
2. O agente lê `curadoria_betas.conteudo.escaladas` via MCP, despacha lotes em paralelo para sub-agentes `AvaliadorBetas` e move os candidatos pontuados (com `llm_confidence_score` e `llm_reasoning`) de `betas_nao_scorados` para `betas_nao_revisados`.

---

## 3. Revisão Humana 1 a 1 e Publicação Limpa

1. Na aba **Betas** do Editor Aresta, revise os cards individualmente (com preview de thumbnail resolvido e cacheado offline pelo `ProvedorImagemAresta`):
   - **✅ Aprovar (1 a 1)**: move a mídia limpa (`url`, `titulo`, `fonte`) para `Escalada.betas` (persistida no `.md` do setor e publicada no `compilado.binarypb`).
   - **❌ Rejeitar (1 a 1)**: move a mídia para `betas_rejeitados` (persistida em `curadoria_betas.md` para impedir re-scraping futuro da mesma URL, mas omitida do `compilado.binarypb`).
   - **↩️ Restaurar (1 a 1)**: devolve um item de `betas_rejeitados` para `betas_nao_scorados`.
2. Salve o croqui (`Ctrl+S` ou botão **Salvar**). Apenas `Escalada.betas` é incluído no `compilado.binarypb`, enquanto `curadoria_betas.md` preserva o estado de curadoria e bloqueio de URLs rejeitadas no repositório.
