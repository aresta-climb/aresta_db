---
name: avaliar_betas_croqui
description: Avalia e pontua candidatos em betas_nao_scorados do croqui aberto no Editor Aresta via MCP usando sub-agentes AvaliadorBetas e move-os para betas_nao_revisados.
---

# Avaliação e Pontuação de Betas Não Scorados (100% via MCP)

Sua missão é ler as entradas de `curadoria_betas.conteudo.escaladas` do croqui aberto no **Editor Aresta** via MCP, avaliar todos os candidatos em `betas_nao_scorados` usando sub-agentes `AvaliadorBetas` em paralelo e promover os candidatos pontuados para `betas_nao_revisados` (ordenados por `llm_confidence_score` decrescente).

> [!CAUTION]
> **Regras Inegociáveis de Curadoria:**
> - **NUNCA** promova candidatos automaticamente via MCP para `Escalada.betas` nem para `betas_rejeitados`. A aprovação e a rejeição final (1 a 1 ou pelos botões de lote por score) são **exclusivas da revisão humana** na aba **Betas** do Editor Aresta.
> - **NUNCA** edite manualmente o arquivo `curadoria_betas.md` no disco (`write_file`, `edit_file`). Todas as mutações devem ser feitas via ferramentas MCP do Editor (`aresta_alterar_campo`, `aresta_adicionar_repeated`, `aresta_remover_repeated`, `aresta_alterar_em_lote`) para preservar o histórico de Undo/Redo.

---

## 1. Leitura Paginada dos Candidatos Não Scorados via MCP

> [!TIP]
> **Escalabilidade para Croquis de 1.000+ Vias:**
> **NUNCA** chame `aresta_obter_arvore(alvo="curadoria_betas.conteudo")` no croqui inteiro para buscar candidatos pendentes — em croquis grandes, `betas_rejeitados` acumula milhares de URLs descartadas e gera payloads de vários megabytes.
> Use **sempre** a ferramenta dedicada `aresta_listar_betas_nao_scorados`, que já filtra apenas escaladas com `betas_nao_scorados` não vazios, omite `betas_rejeitados` e já retorna os metadados enriquecidos da escalada (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_uid`, `setor_nome`, `pico_nome` e `conquistadores`).

1. Chame `aresta_status_workspace()` para identificar o `id_croqui` ativo.
2. Chame `aresta_listar_betas_nao_scorados(offset=0, limite=25)` (opcionalmente filtrando por `alvo_setor`) para obter a primeira página de escaladas com candidatos pendentes:
   - Cada item retornado em `escaladas` já contém `indice_curadoria` (o índice `<idx>` em `curadoria_betas.conteudo.escaladas.<idx>`), os metadados completos da via/boulder e as listas atuais de `betas_nao_scorados` e `betas_nao_revisados`.
3. Caso o croqui ainda não tenha passado pela coleta de betas (`total_escaladas_pendentes == 0`), consulte a skill `coletar_betas_croqui` (`aresta_coletar_betas`).
4. Se `tem_mais == true`, processe e grave a página atual (Passos 2 e 3 abaixo) e em seguida busque a próxima página com `aresta_listar_betas_nao_scorados(offset=0, limite=25)` (como as escaladas avaliadas têm `betas_nao_scorados` limpo para `[]`, elas saem automaticamente da fila pendente!).

---

## 2. Calibração de Score (`llm_confidence_score`) e Avaliação Paralela (`AvaliadorBetas`)

> [!IMPORTANT]
> **Atenção à régua de 80% (Aprovação em Lote na UI):**
> Na seção `2. Betas Não Revisados` da aba **Betas**, o revisor humano dispõe do botão **`✅ Aprovar >= 80%`** e **`❌ Rejeitar < 80%`**. Portanto, **qualquer candidato que receba `llm_confidence_score >= 80` entrará diretamente na escalada publicada** se o revisor utilizar a aprovação automática em lote!
>
> Use rigorosamente a seguinte calibração de notas:
> - **`>= 80` (Aprovação direta segura)**: O vídeo, reel, post ou relato de blog é comprovadamente sobre a escalada específica daquele pico/setor e mostra a escalada da via/boulder ou traz relato técnico/beta útil dos movimentos.
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
- Compare o nome da via, grau, modalidade, setor, pico e cidade com o título, URL e snippets da mídia.
- Atribua um score inteiro de confiança de 0 a 100 (llm_confidence_score) seguindo rigorosamente a régua:
  * >= 80: Certeza de que é sobre a via específica neste pico E contém vídeo/fotos da escalada ou relato de beta (elegível para aprovação automática em lote >= 80%).
  * 50 a 79: Ambíguo ou apenas menção superficial (exige revisão humana 1 a 1).
  * < 30: Ruído, homônimo em outro local, ou páginas que apenas referenciam/incorporam PDFs de croquis ou guias antigos (ex.: Scribd, Issuu, agregadores).
- Escreva uma justificativa curta e objetiva em português (llm_reasoning) explicando por que o candidato recebeu aquela nota.
Retorne os candidatos avaliados estruturados por escalada_uid."""
   )
   ```
2. Divida as escaladas com `betas_nao_scorados` em lotes de 5 a 10 escaladas e invoque os sub-agentes em paralelo via `invoke_subagent`.

---

## 3. Gravação em `betas_nao_revisados` via MCP

Para cada escalada avaliada (`curadoria_betas.conteudo.escaladas.<idx>`):

1. Monte a nova lista de `betas_nao_revisados` combinando os itens já existentes em `betas_nao_revisados` com os candidatos recém-avaliados (preenchendo `resultado_llm.llm_confidence_score` e `resultado_llm.llm_reasoning`), **ordenada de forma decrescente por `llm_confidence_score`**.
2. Atualize o nó da escalada em `curadoria_betas.conteudo.escaladas.<idx>` via `aresta_alterar_em_lote` ou `aresta_alterar_campo`:
   - Defina `betas_nao_revisados` com os candidatos avaliados e ordenados.
   - Limpe `betas_nao_scorados` (`[]`) para os candidatos que já foram promovidos para `betas_nao_revisados`.
3. Chame `aresta_salvar()` ao final caso o usuário tenha solicitado persistência imediata, ou informe ao usuário que os candidatos já estão prontos para revisão (1 a 1 ou em lote `>= 80%` / `< 80%`) na seção **2. Betas Não Revisados** da aba **Betas** do Editor Aresta.
