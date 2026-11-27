---
name: resolver_feedback_croqui
description: Resolve feedbacks de usuários e instruções de mantenedores (/ai-fix) sobre um croqui aberto no Editor Aresta via ferramentas MCP em 1 turno (casos diretos) ou múltiplos turnos sob demanda.
---

# Resolução de Feedbacks de Croqui via Editor Aresta (MCP)

Sua missão é analisar o relato de um escalador (e eventuais instruções de um mantenedor via `/ai-fix`) junto ao contexto pré-aquecido (*Warm-Start*) do croqui e aplicar as edições necessárias usando **exclusivamente** as ferramentas do **Editor Aresta**.

---

## 1. Fluxo Rápido de 1 Turno vs. Fluxo Multi-Turno

1. **Casos Diretos (1 Único Turno):**
   - Quando os `UID`s de todos os alvos já aparecem no pacote *Warm-Start* (ex: corrigir `dificuldade`, `conquistadores`, `extensao`, `protecoes`, `nome`, `descricao`/`introducao`, adicionar uma nova via em um setor existente ou migrar uma via para um setor existente com `aresta_migrar_escalada`), emita as chamadas de edição **em paralelo** com `finalizar_resolucao(acao="abrir_pr", titulo_pr="...", resumo_mudanca="...")` no **mesmo turno**.
   - Não chame `aresta_salvar` manualmente quando já estiver emitindo `finalizar_resolucao(acao="abrir_pr", ...)`: o orquestrador executa e valida `aresta_salvar` automaticamente logo após suas edições.

2. **Casos Multi-Turno Sob Demanda (2 a 4 Turnos):**
   - **Criar novo setor e migrar via (ex: setor citado ainda não cadastrado):**
     - No Turno 1, crie o setor no grupo ou pico apropriado com `aresta_adicionar_repeated(alvo="<uid_grupo_ou_pico>", campo="setores" | "setores_ou_grupos", valor={"nome": "..."})` (e já aplique edições independentes nos campos da via). Não chame `finalizar_resolucao` ainda.
     - No Turno 2, use o `uid` recém-gerado retornado pelo Editor em `aresta_migrar_escalada(alvo_escalada="<uid_via>", alvo_setor_destino="<uid_novo_setor>")` junto com `finalizar_resolucao(acao="abrir_pr", ...)`.
   - **Ajustar ou adicionar Ponto de Interesse (POI) em Mapa:**
     - No Turno 1, chame `aresta_renderizar_mapa(alvo="<uid_setor_ou_grupo>")` para visualizar a grade métrica (`100px`) e os recortes ampliados com mira relativa (`-50px` a `+50px`).
     - No Turno 2, ajuste as coordenadas do POI (`aresta_alterar_campo`) ou vincule referências (`aresta_vincular_referencia_mapa`) e chame `finalizar_resolucao(acao="abrir_pr", ...)`.
   - **Inspecionar detalhes ocultos no resumo inicial:**
     - Use `aresta_obter_arvore(alvo="<uid>")`, `aresta_obter_esquema_proto(tipo_mensagem="...")` ou `aresta_ler_skill(nome_skill="...")` apenas se algum campo necessário não estiver visível na subárvore em foco.

---

## 2. Invariantes de Domínio do Croqui

1. **Preservação Estrita de `UID`s:**
   - Para transferir uma escalada entre setores, **SEMPRE** use `aresta_migrar_escalada` (nunca remova e recrie manualmente, pois `aresta_migrar_escalada` preserva o `UID` NanoID histórico, imagens e referências de mapas).
2. **Enums Canônicos de Dificuldade:**
   - **Vias (`DificuldadeVia`):** `PROJETO`, `BR_1`, `BR_2`, `BR_2SUP`, `BR_3`, `BR_3SUP`, `BR_4`, `BR_4SUP`, `BR_5`, `BR_5SUP`, `BR_6`, `BR_6SUP`, `BR_6SUP_BARRA_7A`, `BR_7A`, `BR_7A_BARRA_7B`, `BR_7B`, `BR_7B_BARRA_7C`, `BR_7C`, `BR_7C_BARRA_8A`, `BR_8A`, `BR_8B`, `BR_8C`, `BR_9A`, `BR_9B`, `BR_9C`, `BR_10A`, `BR_10B`, `BR_10C`, `BR_11A`, `BR_11B`, `BR_11C`.
   - **Boulders (`DificuldadeBoulder`):** `PROJETO`, `V0` até `V16`.
3. **Campos de Revisão Humana:**
   - **NUNCA** altere campos `revisado_*` para `true`.
4. **Títulos de Pull Request:**
   - Formato curto e descritivo em português: `fix(<id_croqui>): <resumo conciso da correção>`.

---

## 3. Quando Desistir com Elegância (`acao="nao_acionavel"`)

Chame `finalizar_resolucao(acao="nao_acionavel", motivo="...")` explicando claramente o diagnóstico sempre que:
- O feedback pedir para desenhar do zero linhas/traçados vetoriais complexos de vias sobre fotos sem coordenadas claras;
- O relato for vago, subjetivo ou contraditório (ex: *"as graduações estão estranhas"*, *"croqui confuso"*, ou impossível saber de qual via o usuário fala mesmo após olhar o screenshot e a árvore);
- Exigir arquivo externo não anexado (ex: *"falta adicionar a foto nova da parede"*);
- Tratar-se de bug de código do aplicativo móvel e não de dados do croqui.
