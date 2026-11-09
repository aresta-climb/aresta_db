# Design

## Context

O módulo `coleta_de_betas` foi originalmente construído em torno de scripts de linha de comando que geravam arquivos soltos (`vias_extraidas.yaml`, `candidatos_brutos.yaml`, `betas_pendentes.binarypb`) e modificavam os arquivos `.md` de setores diretamente no disco, por fora do Editor Aresta. Desde então, o ecossistema evoluiu para:
1. Identificadores universais permanentes NanoID de 14 caracteres (`uid`) em todas as escaladas, setores, grupos e croquis.
2. Arquitetura MVC estrita no Editor (`CroquiModel` + `CroquiController` + `GerenciadorHistorico` com `QUndoCommand` e diário de recuperação).
3. Padrão `ONEOF_CONTEUDO` no `croqui.proto` para arquivos externos (como `ArquivoMapas` -> `mapas_gerais.md`), em que o `CroquiModel` carrega o conteúdo para a árvore Protobuf em memória durante a sessão de edição e o extrai de volta para `.md` no salvamento.
4. Servidor MCP embutido no Editor (`editor/mcp/servidor.py`) expondo a árvore Protobuf para agentes do Antigravity.

Consulte `proposal.md` para a motivação completa da mudança.

## Goals / Non-Goals

**Goals:**
- Manter `MidiaBeta` (em `Escalada.betas` e `betas_rejeitados`) estritamente limpo (`url`, `titulo`, `fonte`), suportando `YOUTUBE`, `INSTAGRAM` e `BLOG`, sem `thumbnail_url` nem metadados transitórios de IA/scraping.
- Isolar os dados de curadoria (`betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados`) em um único arquivo Markdown externo por croqui (`curadoria_betas.md`) vinculado a `Croqui.curadoria_betas` via `ONEOF_CONTEUDO` e indexado por `escalada_uid`, mantendo os arquivos `setor_*.md` exclusivos para `betas` aprovados e omitindo `curadoria_betas` de `compilado.binarypb` e `compilado.yaml`.
- Integrar a coleta (Wizard com seleção de vias e barra de progresso), o scraping de blogs (com janela de contexto de $\pm 300$ caracteres), a avaliação via skill MCP e a curadoria 1 a 1 (4 seções expansíveis na aba **Betas** e atalho na aba **Dados**) ao `CroquiController` com suporte completo a Undo/Redo.
- Resolver miniaturas de pré-visualização on-the-fly estilo WhatsApp (YouTube ID direto + OpenGraph `og:image` para Blog/Instagram) utilizando cache persistente em disco (`ProvedorImagemAresta`).

**Non-Goals:**
- Incluir links de betas no banco `catalogo.db` ou sincronizá-los no Cloudflare D1 (os betas publicados residem exclusivamente em `Escalada.betas` dentro do `compilado.binarypb`).
- Fornecer botões de aprovação em massa (bulk approval) ou limpeza destrutiva em massa na interface de curadoria.
- Fazer o Editor invocar APIs/SDKs de LLM diretamente por conta própria fora do fluxo de agente MCP do Antigravity.

## Decisions

### 1. Separação entre `MidiaBeta` e `CandidatoMidiaBeta` + `ArquivoCuradoriaBetas` (`ONEOF_CONTEUDO`)

- **Escolha**:
  Em `aresta_api/proto/beta.proto`:
  ```protobuf
  message FonteMidia {
    enum Enum {
      INDEFINIDO = 0;
      YOUTUBE = 1;
      INSTAGRAM = 2;
      BLOG = 3;
    }
  }

  message MidiaBeta {
    string url = 1;
    string titulo = 2;
    FonteMidia.Enum fonte = 3;
  }

  message CandidatoMidiaBeta {
    MidiaBeta midia = 1;
    ResultadoLLMBeta resultado_llm = 2;
    bool match_multiplas_fontes = 3;
    bool match_nome_no_snippet = 4;
    repeated string snippets = 5;
  }

  message CuradoriaBetasEscalada {
    string escalada_uid = 1;
    repeated CandidatoMidiaBeta betas_nao_scorados = 2;
    repeated CandidatoMidiaBeta betas_nao_revisados = 3;
    repeated MidiaBeta betas_rejeitados = 4;
  }

  message ColecaoCuradoriaBetas {
    repeated CuradoriaBetasEscalada escaladas = 1;
  }
  ```
  E em `aresta_api/proto/croqui.proto`:
  - `ArquivoCuradoriaBetas` segue o mesmo contrato `ONEOF_CONTEUDO` de `ArquivoMapas`, sendo referenciado em `Croqui.curadoria_betas` (com `(aresta.formato_na_ui) = INVISIVEL` para não poluir o formulário raiz do Croqui na aba Dados) e persistido em `curadoria_betas.md` apenas quando houver entradas não vazias.
- **Racional**:
  - Os arquivos `setor_*.md` jamais sofrem churn de Git durante scraping, avaliação por IA ou rejeição de links; apenas aprovações tocam o `setor_*.md`.
  - Em memória no `CroquiModel`, `croqui.curadoria_betas.conteudo` faz parte da mesma árvore Protobuf que `escalada.betas`. Assim, promover ou rejeitar um item usa comandos normais (`CmdMacro` no `CroquiController`), preservando `Ctrl+Z`/`Ctrl+Y` e visibilidade via MCP.
  - No compilador (`preparar_submissao_lib.py`), após verificar pendências para emissão de `AVISO`, basta executar `croqui_pb.ClearField("curadoria_betas")` antes de serializar `compilado.binarypb` e `compilado.yaml`.
- **Alternativas consideradas**:
  - *Guardar as 4 listas dentro de `Escalada` nos arquivos `setor_*.md`*: Descartado porque poluiria os `.md` dos setores com textos longos de snippets, justificativas de LLM e listas de URLs rejeitadas.

### 2. Extração de Blogs em 2 Estágios com Recorte de Contexto e Blocklist Integrada

- **Escolha**:
  - O coletor unificado recebe o conjunto de URLs já conhecidas da escalada (união de `escalada.betas`, `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados`, normalizadas sem parâmetros de tracking) e descarta imediatamente qualquer URL já presente.
  - Para `FonteMidia.BLOG`, a busca utiliza query ancorada (`"<nome_escalada>" "<nome_pico_ou_setor>" (escalada OR via OR boulder) -site:youtube.com -site:instagram.com`).
  - O extrator de blogs faz download do HTML da página (com cache em memória por URL durante a execução do lote para não baixar o mesmo artigo múltiplas vezes para vias do mesmo setor), remove tags de script/estilo/navegação, verifica a presença de termos do domínio de escalada e recorta janelas de $\pm 300$ caracteres ao redor de cada ocorrência de `nome_escalada`, salvando-as em `CandidatoMidiaBeta.snippets`.
- **Racional**:
  - Postagens de blog quase sempre cobrem um setor ou pico inteiro citando dezenas de vias no corpo do texto. O snippet do buscador (~150 caracteres) frequentemente trunca a parte que descreve a via específica; recortar a janela de $\pm 300$ caracteres ao redor do nome da via entrega tanto para o sub-agente `AvaliadorBetas` quanto para o revisor humano o trecho exato do artigo.

### 3. Provedor de Imagens (`ProvedorImagemAresta`) com Resolução Estilo WhatsApp e Cache Offline

- **Escolha**:
  - Criar/integrar o `ProvedorImagemAresta` no Python/PySide6 utilizando um diretório de cache persistente local indexado pelo hash SHA-256 da URL canônica da mídia (`MidiaBeta.url`).
  - Estratégia de resolução por fonte:
    1. **YouTube**: Extração determinística do ID de 11 caracteres via regex (`watch?v=`, `youtu.be/`, `shorts/`) -> download de `https://i.ytimg.com/vi/<id>/hqdefault.jpg`.
    2. **Blog / Instagram**: Requisição HTTP leve buscando `<meta property="og:image">` / `twitter:image` no `<head>` da página (usando `User-Agent` compatível com preview de links) e salvando os bytes da imagem diretamente no cache offline sob a chave da URL do post.
    3. **Fallback**: Caso offline e sem cache prévio, ou caso o domínio bloqueie a extração da imagem, renderiza o `QPixmap` temático da fonte (YouTube / Instagram / Blog).
- **Racional**:
  - Elimina `thumbnail_url` do Protobuf e evita links quebrados (`403 Forbidden`) de CDNs temporárias (como `cdninstagram.com`), pois os bytes da imagem passam a ser cacheados localmente na primeira visualização.

### 4. Fluxo de UI no Editor (Aba Dados + Aba Betas com 4 Expandos + Wizard + Skill MCP)

- **Escolha**:
  ```text
  +---------------------------------------------------------------------------+
  |                    ARQUITETURA DE UI E TRANSICOES MVC                     |
  +---------------------------------------------------------------------------+

   [Aba Dados: Ficha da Escalada]
    - Card "Betas da Escalada":
      * Lista/edicao rapida de `escalada.betas` (aprovados)
      * Resumo: "X aprovados | Y aguardando revisao | Z nao scorados"
      * Botao [Abrir na Revisao de Betas] ---> foca `page:betas/<escalada_uid>`

   [Aba Betas: PainelCuradoria]
    - Topo: Filtro por Escalada/Setor + Botao [Coletar Betas... (Wizard)]
    - 4 Secoes Expansiveis (Expandos) por Escalada:
      1. [Nao Revisados] (`betas_nao_revisados`, ordenados por score LLM desc)
         -> Card com [Aprovar] (move p/ `betas`) e [Rejeitar] (move p/ `betas_rejeitados`)
      2. [Nao Scorados] (`betas_nao_scorados`)
         -> Banner com instrucao/botao para acionar Skill MCP `avaliar_betas_croqui`
         -> Card com [Aprovar] e [Rejeitar] individuais
      3. [Betas Aprovados] (`escalada.betas`)
         -> Card com edicao de titulo/URL e botao [Mover para Rejeitados]
      4. [Betas Rejeitados] (`betas_rejeitados`, recolhido por padrao)
         -> Card com botao [Restaurar / Aprovar] (move p/ `betas`)
  ```
  - Todas as transições entre listas são executadas por métodos no `CroquiController` agrupados em `CmdMacro`, garantindo reversibilidade total com `Ctrl+Z`.

## Risks / Trade-offs

- **[Rate-limit ou bloqueio de scraping em buscas grandes]** → O Wizard permite selecionar subconjuntos de setores/escaladas (com filtro padrão para escaladas sem betas aprovados), exibe progresso passo a passo com opção de cancelamento preservando o que já foi coletado, e usa cache em memória por URL de blog.
- **[Expiração ou bloqueio de `og:image` no Instagram]** → O `ProvedorImagemAresta` persiste os bytes da imagem em disco na primeira resolução bem-sucedida e possui fallback visual imediato quando a imagem não puder ser obtida.
