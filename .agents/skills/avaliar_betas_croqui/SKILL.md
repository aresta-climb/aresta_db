---
name: avaliar_betas_croqui
description: Avalia e pontua candidatos em betas_nao_scorados do croqui aberto no Editor Aresta via MCP usando sub-agentes AvaliadorBetas e move-os para betas_nao_revisados.
---

# Avaliação e Pontuação de Betas Não Scorados (100% via MCP `editor-aresta`)

Sua missão é ler as entradas de `curadoria_betas.conteudo.escaladas` do croqui alvo no **Editor Aresta** via servidor MCP **`editor-aresta`**, avaliar todos os candidatos em `betas_nao_scorados` e promover os candidatos pontuados para `betas_nao_revisados` (ordenados por `llm_confidence_score` decrescente).

> [!CAUTION]
> **Regras Inegociáveis de Curadoria:**
> - **NUNCA** promova candidatos automaticamente via MCP para `Escalada.betas` nem para `betas_rejeitados`. A aprovação e a rejeição final (1 a 1 ou pelos botões de lote por score) são **exclusivas da revisão humana** na aba **Betas** do Editor Aresta.
> - **NUNCA** chame `aresta_remover_betas` de forma autônoma durante a pontuação em lote; essa ferramenta é **exclusiva para pedidos explícitos do usuário ou mantenedor**.
> - **NUNCA** edite manualmente o arquivo `curadoria_betas.yaml` ou `.md` no disco (`write_file`, `edit_file`). Todas as mutações devem ser feitas via ferramentas MCP do `editor-aresta` (use **`aresta_pontuar_betas`** para registrar as notas) para preservar `snippets`, `midia` e o histórico de Undo/Redo.

---

## 1. Identificação do `id_croqui` e Leitura Paginada via MCP (`editor-aresta`)

> [!IMPORTANT]
> **Suporte a Múltiplos Croquis Abertos (`id_croqui`):**
> - Se o usuário já informou o `id_croqui` (ex.: no prompt copiado da aba **Betas**), passe `id_croqui="<id_croqui>"` em **TODAS** as chamadas às ferramentas do `editor-aresta` (`aresta_status_workspace`, `aresta_listar_betas_nao_scorados`, `aresta_pontuar_betas`, `aresta_adicionar_betas_revisao`, `aresta_remover_betas`, `aresta_salvar`).
> - Se o `id_croqui` não foi informado, chame primeiro `aresta_listar_croquis()` (que funciona sem `id_croqui`) para descobrir os croquis em `abertos`; havendo mais de um croqui aberto, selecione o alvo ou pergunte ao usuário antes de prosseguir.

> [!TIP]
> **Escalabilidade para Croquis de 1.000+ Vias:**
> **NUNCA** chame `aresta_obter_arvore(alvo="curadoria_betas.conteudo")` no croqui inteiro para buscar candidatos pendentes — em croquis grandes, `betas_rejeitados` acumula milhares de URLs descartadas e gera payloads de vários megabytes.
> Use **sempre** a ferramenta dedicada `aresta_listar_betas_nao_scorados`, que já filtra apenas escaladas com `betas_nao_scorados` não vazios, omite `betas_rejeitados` e já retorna os metadados enriquecidos da escalada (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_uid`, `setor_nome`, `pico_nome`, `pico_cidade`, `croqui_nome` e `conquistadores`).

1. Chame `aresta_status_workspace(id_croqui="<id_croqui>")` (omitindo `id_croqui` apenas se houver 1 croqui aberto) para confirmar o `id_croqui` ativo.
2. Chame `aresta_listar_betas_nao_scorados(id_croqui="<id_croqui>", offset=0, limite=25)` (opcionalmente filtrando por `alvo_setor`) para obter a primeira página de escaladas com candidatos pendentes:
   - Cada item retornado em `escaladas` já contém `indice_curadoria` (o índice `<idx>` em `curadoria_betas.conteudo.escaladas.<idx>`), os metadados completos da via/boulder e as listas atuais de `betas_nao_scorados` e `betas_nao_revisados`.
3. Caso o croqui ainda não tenha passado pela coleta de betas (`total_escaladas_pendentes == 0`), consulte a skill `coletar_betas_croqui` (`aresta_coletar_betas`).
4. Se `tem_mais == true`, processe e grave a página atual (Passos 2 e 3 abaixo) e em seguida busque a próxima página com `aresta_listar_betas_nao_scorados(id_croqui="<id_croqui>", offset=0, limite=25)` (como as escaladas avaliadas têm `betas_nao_scorados` limpo, elas saem automaticamente da fila pendente!).

---

## 2. Calibração de Score (`llm_confidence_score`) e Avaliação Paralela (`AvaliadorBetas`)

> [!IMPORTANT]
> **Atenção à régua de 80% (Aprovação em Lote na UI):**
> Na seção `2. Betas Não Revisados` da aba **Betas**, o revisor humano dispõe do botão **`✅ Aprovar >= 80%`** e **`❌ Rejeitar < 80%`**. Portanto, **qualquer candidato que receba `llm_confidence_score >= 80` entrará diretamente na escalada publicada** se o revisor utilizar a aprovação automática em lote!
>
> Use rigorosamente a seguinte calibração de notas:
> - **`>= 80` (Aprovação direta segura)**: O vídeo, reel, post ou relato de blog é comprovadamente sobre a escalada específica daquele pico/cidade (`pico_nome` / `pico_cidade` / `croqui_nome`, atenção a homônimos em outros estados como Pedra Grande de Atibaia vs. Igarapé) e mostra a escalada da via/boulder ou traz relato técnico/beta útil dos movimentos.
> - **`50` a `79` (Dúvida / Revisão manual 1 a 1)**: Menciona a via mas tem pouca informação de beta, é apenas uma foto posada na base sem movimentos ou há ambiguidade moderada de homônimo.
> - **`< 30` (Descarte seguro em lote)**: Ruído, via homônima em outro estado/pico, ou páginas que apenas referenciam/incorporam PDFs de croquis ou guias antigos (como Scribd, Issuu, Academia.edu, ResearchGate ou diretórios/agregadores genéricos).

1. Defina o sub-agente especialista `AvaliadorBetas` via `define_subagent`:
   ```python
   define_subagent(
       Name="AvaliadorBetas",
       Description="Avalia relevância semântica e correspondência de vídeos, reels e relatos de blog para escaladas",
       SystemPrompt="""Você é um especialista em escalada em rocha e boulder no Brasil.
Sua missão é avaliar candidatos a beta (YouTube, Instagram, TikTok, Facebook e Blogs) para escaladas específicas de um croqui.
Para cada candidato fornecido em betas_nao_scorados:
- Compare o nome da via, grau, modalidade, setor, pico_nome, pico_cidade e croqui_nome com o título, URL e snippets da mídia (cuidado com picos homônimos em outras cidades/estados).
- Atribua um score inteiro de confiança de 0 a 100 (llm_confidence_score) seguindo rigorosamente a régua:
  * >= 80: Certeza de que é sobre a via específica neste pico/cidade E contém vídeo/fotos da escalada ou relato de beta (elegível para aprovação automática em lote >= 80%).
  * 50 a 79: Ambíguo ou apenas menção superficial (exige revisão humana 1 a 1).
  * < 30: Ruído, homônimo em outro local, ou páginas que apenas referenciam/incorporam PDFs de croquis ou guias antigos (ex.: Scribd, Issuu, agregadores).
- Escreva uma justificativa curta e objetiva em português (llm_reasoning) explicando por que o candidato recebeu aquela nota.
Retorne apenas {escalada_uid, avaliacoes: [{url, llm_confidence_score, llm_reasoning}]}."""
   )
   ```
2. Divida as escaladas com `betas_nao_scorados` em lotes de 5 a 10 escaladas e invoque os sub-agentes em paralelo via `invoke_subagent`.
   - **Clientes MCP sem `define_subagent`/`invoke_subagent` (ex.: Cursor, Claude Desktop, Codex):** utilize o mecanismo equivalente de subagentes do cliente ou avalie diretamente em lotes de 5 a 10 escaladas aplicando rigorosamente a mesma régua de calibração acima.

---

## 3. Gravação Atômica em `betas_nao_revisados` via `aresta_pontuar_betas`

1. Chame a ferramenta dedicada **`aresta_pontuar_betas`** no MCP `editor-aresta` passando `id_croqui` (quando aplicável) e a lista enxuta `escaladas`:
   ```json
   {
     "id_croqui": "<id_croqui>",
     "escaladas": [
       {
         "escalada_uid": "uid_da_escalada",
         "avaliacoes": [
           {
             "url": "https://youtube.com/watch?v=...",
             "llm_confidence_score": 95,
             "llm_reasoning": "Vídeo mostra a cadena completa da via no pico e cidade corretos."
           }
         ]
       }
     ]
   }
   ```
   A ferramenta valida todas as URLs e scores antecipadamente (*fail-fast*), copia os objetos `CandidatoMidiaBeta` diretamente da memória RAM preservando integralmente `midia`, `snippets` e flags de match, mescla e reordena `betas_nao_revisados` por `llm_confidence_score` decrescente, remove os itens avaliados de `betas_nao_scorados` em um único `CmdMacro` atômico e retorna o total restante na fila.
2. Chame `aresta_salvar(id_croqui="<id_croqui>")` ao final caso o usuário tenha solicitado persistência imediata, ou informe ao usuário que os candidatos já estão prontos para revisão (1 a 1 ou em lote `>= 80%` / `< 80%`) na seção **2. Betas Não Revisados** da aba **Betas** do Editor Aresta.

---

## 4. Adição para Revisão e Remoção Explícita via MCP

- **Enfileirar novo link para revisão (`aresta_adicionar_betas_revisao`):** quando o usuário enviar links ou você localizar novos vídeos/relatos fora da coleta automática, chame `aresta_adicionar_betas_revisao(id_croqui="<id_croqui>", itens=[{escalada_uid, url, titulo?, fonte?, snippets?, llm_confidence_score?, llm_reasoning?}])`. Se incluir nota + justificativa, o item entra direto em `betas_nao_revisados`; sem nota, entra em `betas_nao_scorados`. URLs que estavam em `betas_rejeitados` são resgatadas de volta para revisão (itens já aprovados em `Escalada.betas` permanecem intactos).
- **Remover beta específico sob pedido explícito (`aresta_remover_betas`):** apenas quando o usuário ou mantenedor pedir explicitamente para remover um beta incorreto, chame `aresta_remover_betas(id_croqui="<id_croqui>", itens=[{escalada_uid, url}], bloquear_futura_coleta=True)` para removê-lo de `Escalada.betas` ou das filas pendentes e registrá-lo em `betas_rejeitados` contra futuras coletas.
