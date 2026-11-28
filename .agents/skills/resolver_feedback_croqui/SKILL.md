---
name: resolver_feedback_croqui
description: Resolve feedbacks de usuários e instruções de mantenedores (/ai-fix) sobre um croqui aberto no Editor Aresta via ferramentas MCP em 1 turno (casos diretos) ou múltiplos turnos sob demanda.
---

# Resolução de Feedbacks de Croqui via Editor Aresta (MCP)

Sua missão é analisar o relato de um escalador (e eventuais instruções de um mantenedor via `/ai-fix`) junto ao contexto pré-aquecido (*Warm-Start*) do croqui e aplicar as edições necessárias usando **exclusivamente** as ferramentas do **Editor Aresta**.

---

## 1. Fluxo Objetivo e Econômico em Turnos

Seja **direto**: não gaste turnos lendo seções textuais, skills não relacionadas ou mapas quando os dados necessários para atender ao relato já constam no pacote *Warm-Start*.

1. **Casos Diretos (1 Único Turno):**
   - Quando os `UID`s de todos os alvos já aparecem no pacote *Warm-Start* (ex: corrigir `dificuldade`, `conquistadores`, `extensao`, `protecoes`, `nome`, `descricao`/`introducao`, adicionar uma nova via em um setor existente ou migrar uma via para um setor já existente com `aresta_migrar_escalada`), emita as chamadas de edição **em paralelo** com `finalizar_resolucao(acao="abrir_pr", titulo_pr="...", resumo_mudanca="...")` no **mesmo turno**.
   - Não chame `aresta_salvar` manualmente: `finalizar_resolucao(acao="abrir_pr", ...)` já executa e valida `aresta_salvar` automaticamente.

2. **Criar Novo Setor e Migrar Via (Exatamente 2 Turnos):**
   - **Turno 1:** Crie o setor no Grupo (`campo="setores"`) ou Pico (`campo="setores_ou_grupos"`) passando `valor={"nome": "Nome do Setor"}` em `aresta_adicionar_repeated` — e já aplique em paralelo quaisquer ajustes de campos na via (`aresta_alterar_campo`). **Não** chame `finalizar_resolucao` no Turno 1 pois você precisa do `uid` gerado.
     - Exemplo em Grupo: `aresta_adicionar_repeated(alvo="<uid_grupo>", campo="setores", valor={"nome": "Setor do Palanque"})`
   - **Turno 2:** Com o `uid` retornado em `structuredContent.uid`, chame `aresta_migrar_escalada(alvo_escalada="<uid_via>", alvo_setor_destino="<uid_novo_setor>")` **em paralelo com** `finalizar_resolucao(acao="abrir_pr", titulo_pr="...", resumo_mudanca="...")` no **mesmo Turno 2**!

3. **Ajustar ou Extrair Ponto de Interesse (POI) em Mapa (2 Turnos):**
   - **Turno 1:** Chame `aresta_renderizar_mapa(alvo="<uid_setor_ou_grupo>")` para visualizar a grade métrica (`100px`) e os recortes com mira relativa (`-50px` a `+50px`).
   - **Turno 2:** Ajuste as coordenadas (`aresta_alterar_campo`) ou referências (`aresta_vincular_referencia_mapa`) **em paralelo com** `finalizar_resolucao(acao="abrir_pr", ...)`.

---

## 2. Invariantes de Domínio do Croqui

1. **Preservação Estrita de `UID`s:**
   - Para transferir uma escalada entre setores, **SEMPRE** use `aresta_migrar_escalada` (nunca remova e recrie manualmente, pois `aresta_migrar_escalada` preserva o `UID` NanoID histórico, imagens e referências de mapas).
2. **Lista `conquistadores` (1 Nome por Item):**
   - `conquistadores` é uma lista `repeated string` onde **cada pessoa deve ser uma string separada** (ex: `["Macena", "Samuel"]`, nunca `["Macena, Samuel"]`). Se um conquistador citado pelo usuário já tiver sido removido mas a lista estiver concatenada por vírgula, normalize-a para itens separados na ocasião.
3. **Enums Canônicos de Dificuldade:**
   - **Vias (`DificuldadeVia`):** `PROJETO`, `BR_1`, `BR_2`, `BR_2SUP`, `BR_3`, `BR_3SUP`, `BR_4`, `BR_4SUP`, `BR_5`, `BR_5SUP`, `BR_6`, `BR_6SUP`, `BR_6SUP_BARRA_7A`, `BR_7A`, `BR_7A_BARRA_7B`, `BR_7B`, `BR_7B_BARRA_7C`, `BR_7C`, `BR_7C_BARRA_8A`, `BR_8A`, `BR_8B`, `BR_8C`, `BR_9A`, `BR_9B`, `BR_9C`, `BR_10A`, `BR_10B`, `BR_10C`, `BR_11A`, `BR_11B`, `BR_11C`.
   - **Boulders (`DificuldadeBoulder`):** `PROJETO`, `V0` até `V16`.
4. **Campos de Revisão Humana:**
   - **NUNCA** altere campos `revisado_*` para `true`.
5. **Betas de Escalada (`aresta_remover_betas` / `aresta_adicionar_betas_revisao`):**
   - Para remover um vídeo/beta incorreto citado no feedback, **SEMPRE** use `aresta_remover_betas(itens=[{"escalada_uid": "<uid_via>", "url": "<url>"}])` em vez de `aresta_remover_repeated`, para que a URL seja movida para `betas_rejeitados` e não volte em futuras coletas.
   - Para encaminhar um novo link sugerido no feedback para revisão humana na aba **Betas**, use `aresta_adicionar_betas_revisao(itens=[{"escalada_uid": "<uid_via>", "url": "<url>", ...}])`.
6. **Títulos de Pull Request:**
   - Formato curto e descritivo em português: `fix(<id_croqui>): <resumo conciso da correção>`.

---

## 3. Quando Desistir com Elegância (`acao="nao_acionavel"`)

Chame `finalizar_resolucao(acao="nao_acionavel", motivo="...")` explicando claramente o diagnóstico sempre que:
- O feedback pedir para desenhar do zero linhas/traçados vetoriais complexos de vias sobre fotos sem coordenadas claras;
- O relato for vago, subjetivo ou contraditório (ex: *"as graduações estão estranhas"*, *"croqui confuso"*, ou impossível saber de qual via o usuário fala mesmo após olhar o screenshot e a árvore);
- Exigir arquivo externo não anexado (ex: *"falta adicionar a foto nova da parede"*);
- Tratar-se de bug de código do aplicativo móvel e não de dados do croqui.
