# Design Técnico: Pipeline PDF 100% via MCP e Múltiplas Janelas

## Context

Atualmente, os fluxos de extração e atualização de croquis em PDF (`processar_croqui_completo.md` e `atualizar_croqui_completo.md`) funcionam de maneira híbrida e frágil:
1. O script `scripts/repartir_pdf.py` fatia o PDF em pastas `partes/` e extrai dados vetoriais em JSON.
2. Subagentes (`converter_parte_croqui_para_markdown`) criam ou editam manualmente arquivos `.md` com YAML Frontmatter e geram `croqui.yaml` (`preencher_croqui_yaml`), sujeitos a erros de sintaxe YAML e perda de `UID`s.
3. Scripts intermediários (`preparar_extracao_de_mapas.py`, `visualizar_mapa_processado.py`, `finalizar_mapas.py`) dependem do `PaddleOCR` (`paddlepaddle`) — uma dependência pesada que não está disponível na instalação padrão do Editor — e manipulam arquivos temporários em `raw_mapas/`.
4. O Editor Aresta impõe uma trava global de instância única (`ArestaEditorSingleInstanceServer`), impedindo que múltiplos croquis sejam abertos em paralelo, e só inicia o `ServidorMCP` após um croqui já estar aberto na `JanelaPrincipal`.

Com o servidor MCP do Editor Aresta já maduro e integrado aos controllers (`CroquiController` e `MapasController`) e ao histórico `QUndoStack`, podemos unificar **100% da interação dos agentes** no protocolo MCP, eliminar o `PaddleOCR` e a edição manual de arquivos `.md`/`.yaml`/`.json`, e permitir múltiplas janelas simultâneas com trava por croqui.

## Goals / Non-Goals

**Goals:**
- **MCP Ativo desde a Tela de Carregamento (`TelaDeCarregamento`)**: Iniciar o `ServidorMCP` imediatamente ao abrir o aplicativo, exibir o botão **"Conectar Agente de IA (MCP)..."** na `TelaDeCarregamento` e expor ferramentas dedicadas para listar, abrir, importar e criar croquis (`aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui`), além de guarda defensiva quando nenhum croqui estiver aberto.
- **Múltiplas Janelas com Trava por Croqui e Proxy MCP na Porta `27378`**: Substituir a trava global de processo único por trava por croqui (`ArestaEditorCroqui_<id_croqui>`), mantendo um registro multi-sessão (`mcp_sessoes.json`) e roteando chamadas da porta primária `27378` para janelas/portas secundárias (`27379+`) via parâmetro opcional `id_croqui`.
- **Transações Atômicas Completas por `UID` (Incluindo Listas `repeated`) e Sem `Undo/Redo` no MCP**: Permitir que `aresta_alterar_campo` substitua declarativamente listas `repeated` inteiras (ex: `escaladas`, `mapas`, `pontos_de_interesse`, `referencias`) dentro de um único `CmdMacro` atômico (preservando `uid`s existentes e gerando NanoIDs para novos), e remover `aresta_desfazer`/`aresta_refazer` do MCP para evitar interferência entre subagentes paralelos.
- **Extração de PDF e Mapas 100% via MCP sem `PaddleOCR`**: Mover `pymupdf` para o grupo `editor`, remover `paddleocr`, expor `aresta_particionar_pdf_croqui` (que fatia o PDF e pré-aloca os esqueletos na árvore Protobuf já com `UID`s) e `aresta_renderizar_mapa` (que retorna blocos intercalados `[Texto, Imagem]` com sementes vetoriais `PyMuPDF`, imagem completa com grade métrica `100px` + réguas graduadas e recortes `120x120px` com mira relativa `-50px..+50px` para cada POI).
- **Remoção de Código Legado e Reescrita das Skills**: Excluir `preparar_extracao_de_mapas.py`, `visualizar_mapa_processado.py`, `finalizar_mapas.py` e `extrair_ocr_lote.py` (e seus testes) e atualizar todas as skills e workflows em `.agents/` para usarem exclusivamente ferramentas MCP.

**Non-Goals:**
- Alterar o funcionamento do `Ctrl+Z` / `Ctrl+Y` (`QUndoStack`) na interface gráfica humana (apenas as tools MCP `aresta_desfazer` e `aresta_refazer` são removidas).
- Permitir que duas janelas editem simultaneamente **o mesmo** `id_croqui` (a trava por croqui garante no máximo 1 janela por `id_croqui`).

## Decisions

### 1. Ciclo de Vida do Servidor MCP, Gestão de Croquis e Guarda "Sem Croqui Aberto"

- **Inicialização no `ControladorAplicativo` (`editor/main.py`)**:
  - O `ServidorMCP` passa a pertencer ao `ControladorAplicativo` (e não apenas à `JanelaPrincipal`), sendo iniciado já no boot do aplicativo antes mesmo de `exibir_tela_carregamento()`.
  - Na `TelaDeCarregamento` (`editor/legacy_views/tela_de_carregamento.py`), adicionamos o botão **"Conectar Agente de IA (MCP)..."** na barra de ações superiores, abrindo o mesmo `DialogoConexaoMcp` já existente.
- **Guarda Defensiva no Despachante MCP**:
  - Todas as ferramentas que operam sobre um croqui aberto (`aresta_obter_arvore`, `aresta_alterar_campo`, `aresta_adicionar_repeated`, `aresta_remover_repeated`, `aresta_mover_repeated`, `aresta_migrar_setor`, `aresta_alterar_imagem`, `aresta_alterar_campo_imagem`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown`, `aresta_adicionar_mapa_arquivo`, `aresta_vincular_referencia_mapa`, `aresta_renderizar_mapa`, `aresta_capturar_canvas`, `aresta_obter_selecao_atual`, `aresta_focar_elemento`, `aresta_status_workspace`, `aresta_compilar`, `aresta_salvar`) verificam se há uma sessão de croqui ativa para o alvo.
  - Caso nenhum croqui esteja aberto (`len(sessoes_abertas) == 0`), retornam imediatamente `ResultadoFerramenta(conteudo=[...], eh_erro=True)` com mensagem clara: *"Nenhum croqui está aberto no Editor Aresta. Use `aresta_listar_croquis` para inspecionar os croquis disponíveis e abra/crie um croqui com `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial` ou `aresta_criar_novo_croqui`."*
- **Quatro Ferramentas de Gestão de Croquis (`editor/mcp/ferramentas_ciclo_vida.py`)**:
  1. `aresta_listar_croquis(busca: str | None = None)`:
     - Retorna `{ "abertos": [...], "em_andamento": [...], "oficiais": [...] }` consultando as sessões ativas, `GerenciadorCroquiExperimental.listar_croquis_em_andamento()` e `GerenciadorCroquiExperimental.buscar_croquis_oficiais(busca)`.
  2. `aresta_abrir_croqui_existente(identificador: str)`:
     - Aceita um `identificador` de croqui em andamento (`<id_croqui>_<timestamp>`) ou pasta local `database/<id_croqui>`.
  3. `aresta_importar_croqui_oficial(id_oficial: str, resumo_edicao: str = "")`:
     - Invoca `GerenciadorCroquiExperimental.criar_croqui_a_partir_de_oficial(id_oficial, resumo_edicao)`, compila o rascunho experimental e o abre.
  4. `aresta_criar_novo_croqui(nome_pico: str, cidade: str, estado: str, pais: str = "br")`:
     - Gera o `id_croqui` canônico via `GerenciadorCroquiExperimental.gerar_id_croqui`, cria a estrutura inicial com `criar_novo_croqui`, compila e abre.
- **Comportamento de Janelas ao Abrir/Criar Croqui**:
  - **Se 0 croquis estão abertos** (aplicativo está na `TelaDeCarregamento`): fecha a `TelaDeCarregamento` e abre a `JanelaPrincipal` na mesma instância com o croqui solicitado.
  - **Se o mesmo `id_croqui` já está aberto** em uma janela (nesta instância ou em outra): traz a janela existente para frente (`elevar_janela`) e retorna os metadados da sessão existente de forma idempotente.
  - **Se outro croqui `"A"` já está aberto e solicita-se abrir `"B"`**: mantém a janela de `"A"` intacta e instancia uma nova `JanelaPrincipal` independente para `"B"` (ou novo processo/sessão registrado em `mcp_sessoes.json`), retornando `id_croqui`, `uid_croqui`, `caminho_database` e `porta_mcp`.

### 2. Múltiplas Janelas / Sessões por Croqui e Roteamento Proxy na Porta `27378`

- **Trava de Instância Única por Croqui (`editor/core/instancia_unica.py`)**:
  - Substituímos a trava global sem escopo por `GerenciadorInstanciaUnica(nome_servidor=f"ArestaEditorCroqui_{id_croqui}")` (mantendo um servidor de controle por janela de croqui aberto) e adicionamos um lockfile (`git_operacao.lock`) em `GerenciadorGit` / `GerenciadorCroquiExperimental` apenas durante operações Git compartilhadas (fetch/worktree).
- **Registro Multi-Sessão (`mcp_sessoes.json` em `editor/mcp/sessao.py`)**:
  - `GerenciadorSessaoMcp` mantém o arquivo `mcp_sessoes.json` (com escrita atômica via arquivo temporário + lock) contendo a lista de sessões ativas (`pid`, `porta`, `id_croqui`, `caminho_database`, `iniciado_em`), além de manter `mcp_sessao.json` apontando para o servidor primário (`27378`) para compatibilidade.
  - Dentro de um mesmo processo ou entre múltiplos processos do Editor, cada `JanelaPrincipal` aberta possui seu próprio contexto (`CroquiModel`, `CroquiController`, `MapasController`, `GerenciadorWorkspace`, `QUndoStack`).
  - O `ServidorMCP` primário na porta `27378`:
    - Se a janela do `id_croqui` solicitado estiver no próprio processo, despacha diretamente para o contexto daquela `JanelaPrincipal` na main thread do Qt.
    - Se a janela do `id_croqui` solicitado estiver em outro processo do Editor (em uma porta secundária `27379+` registrada em `mcp_sessoes.json`), encaminha a chamada JSON-RPC (`tools/call`) via HTTP local para a porta correspondente e devolve a resposta transparente ao cliente MCP.
  - **Resolução de `id_croqui` opcional**:
    - Todas as ferramentas de croqui aceitam `id_croqui: str | None = None`.
    - Se houver exatamente **1** croqui aberto e `id_croqui` for omitido, seleciona automaticamente esse único croqui aberto.
    - Se houver **2 ou mais** croquis abertos e `id_croqui` for omitido, retorna `isError: True` listando os `id_croqui` abertos para desambiguação explícita.

### 3. Particionamento de PDF e Pré-Alocação de Esqueletos (`aresta_particionar_pdf_croqui`)

- **Unificação de `repartir_pdf` com a Árvore Protobuf**:
  - A ferramenta `aresta_particionar_pdf_croqui(caminho_pdf: str, partes: dict[str, list[int]], id_croqui: str | None = None)` executa `repartir_pdf` sobre o diretório temporário de trabalho da sessão (`<pasta_croqui>/.partes_pdf/`), gerando os sub-PDFs, convertendo as imagens da página em `.webp` para a pasta `imagens/` do croqui e salvando os metadados vetoriais (`*_dados.json`) por parte.
  - Em seguida, sincroniza a árvore do `Croqui` via `CroquiController` (em um único `CmdMacro`):
    - Para cada chave em `partes`:
      - `"croqui"`: retorna `uid` da raiz `Croqui`.
      - `"mapas_gerais"`: garante a existência de um `Botao(id="mapas_gerais", colecao_de_mapas=ColecaoDeMapas(...))` (ou reaproveita o existente preservando seu `uid`) e retorna o `uid` da `ColecaoDeMapas`.
      - `"setor_<slug>"`: garante a existência do `Setor(id="<slug>")` e respectivo `Botao` na raiz (se ainda não vinculado a um grupo), preservando o `uid` caso o setor já exista (fluxo de atualização).
      - `"grupo_<slug>"`: garante a existência do `Grupo(id="<slug>")` e respectivo `Botao`, preservando o `uid` existente.
      - `"apendice_<slug>"`: garante a existência do `Botao(id="<slug>", pagina_markdown=...)`, preservando o `uid` existente.
  - Retorna para o orquestrador o dicionário estruturado:
    ```json
    {
      "id_croqui": "...",
      "partes": {
        "setor_principal": {
          "uid": "xK9mP2qR",
          "tipo": "Setor",
          "caminho_pdf": ".../setor_principal.pdf",
          "imagens": ["imagens/img_p3_1.webp", "imagens/img_p4_1.webp"],
          "dados_vetoriais": { ... }
        }
      }
    }
    ```
  - Com isso, o orquestrador pode disparar subagentes em paralelo passando diretamente o `uid` exclusivo de cada parte, garantindo isolamento total.

### 4. Substituição Declarativa de Listas `repeated` em `aresta_alterar_campo` e Remoção de `Undo/Redo`

- **Substituição de Campos `repeated` no `CroquiController.alterar_campo`**:
  - Atualmente, `CroquiController.alterar_campo` rejeita campos `repeated` se não forem indexados (`campo.0`).
  - Passamos a suportar `valor: list` quando o descritor Protobuf do campo for `FD.LABEL_REPEATED`:
    - Para campos `repeated` de submensagens (`escaladas`, `mapas`, `pontos_de_interesse`, `referencias`, `botoes`, `participantes`, etc.):
      1. Converte cada item `dict` da lista em uma instância Protobuf validada usando `_converter_dict_para_mensagem_proto(item_dict, sub_desc)`.
      2. Se o descritor da submensagem possuir o campo `uid`:
         - Se o `dict` já trouxer um `uid` não vazio, **preserva esse `uid`**.
         - Se não trouxer `uid`, gera imediatamente um NanoID único via `gerar_uid(uids_existentes)`.
         - Aplica a mesma regra recursivamente para sub-listas aninhadas (ex: `escaladas[].mapas`, `mapas[].pontos_de_interesse`, `mapas[].referencias`).
    - Dentro de um único `CmdMacro` no `QUndoStack`:
      - Empilha `CmdRemoverRepeated` do último ao primeiro índice atual da lista (`for idx in range(len(lista_atual) - 1, -1, -1)`).
      - Empilha `CmdAdicionarRepeated` para cada novo item validado na ordem declarada.
    - Tanto chamadas individuais `aresta_alterar_campo(alvo=uid, campo="pontos_de_interesse", valor=[...])` quanto chamadas em lote `aresta_alterar_campo(alvo=uid_setor, campos={"nome": "...", "escaladas": [...], "mapas": [...]})` executam tudo dentro de **um único `CmdMacro` atômico** na main thread do Qt.
- **Remoção de `aresta_desfazer` e `aresta_refazer` do MCP**:
  - Removemos `aresta_desfazer` e `aresta_refazer` de `editor/mcp/ferramentas_ciclo_vida.py`.
  - O usuário humano continua podendo desfazer/refazer normalmente pela interface gráfica (`Ctrl+Z`/`Ctrl+Y`), onde cada chamada atômica de um subagente aparece como uma única entrada limpa no histórico (`"Alterar lote em Setor 'Principal'"`).

### 5. Ferramenta `aresta_renderizar_mapa` com Grade Métrica, Réguas e Recortes Intercalados `[Texto, Imagem]`

- **Módulo de Renderização Visual de Mapas (`editor/mcp/renderizador_mapa_mcp.py`)**:
  - Implementamos uma biblioteca pura e testável (`editor/mcp/renderizador_mapa_mcp.py` + `renderizador_mapa_mcp_test.py`) usando `QImage` / `QPainter` (ou `Pillow`, já presente no `editor`) que não depende de `PaddleOCR`:
    1. **Imagem Completa com Grade Métrica e Réguas**:
       - Carrega a imagem do `Mapa` (`caminho_imagem_mapa`).
       - Desenha uma grade métrica semitransparente a cada `100px` (linhas secundárias a cada `50px`) e faixas de régua graduadas no topo (`X`) e na esquerda (`Y`) com marcações numéricas de `0` até `largura`/`altura`.
       - Desenha todos os `pontos_de_interesse` atualmente presentes no `Mapa` em vermelho (pontos como círculos com cruz central, linhas/polígonos com seus vértices numerados e o `rotulo` ao lado).
    2. **Recortes Ampliados (`Crops`) por Ponto de Interesse**:
       - Para cada POI em `mapa.pontos_de_interesse`, calcula seu ponto central `(cx, cy)` (para `ponto`: `(x, y)`; para `linha`/`poligono`: centroide ou vértice inicial/médio) e recorta uma janela de `120x120px` (ampliada para `240x240px` para legibilidade da LLM) centrada em `(cx, cy)`.
       - Desenha no recorte uma mira central `(0, 0)` e réguas relativas nas bordas variando de `-50px` a `+50px` (com marcações a cada `10px`), permitindo que a LLM veja exatamente quantos pixels o marcador está deslocado em relação ao número/círculo real na imagem (ex: `dx = +12, dy = -8`).
  - **Extração de Candidatos Vetoriais via `PyMuPDF`**:
    - Quando o mapa foi originado de um PDF particionado (ou quando `dados_vetoriais` estiverem disponíveis para a imagem), inclui no primeiro bloco de texto os textos e desenhos vetoriais já convertidos para coordenadas de pixel `(x, y)` da imagem.
  - **Formato de Retorno Intercalado (`content: list[dict]`)**:
    - O `ServidorMCP` passa a suportar blocos intercalados arbitrários em `ResultadoFerramenta` (ou preserva a ordem de `blocos: list[dict]`), permitindo que `aresta_renderizar_mapa` retorne exatamente:
      - `content[0]` (`type: "text"`): Metadados do mapa (`uid`, `caminho_imagem_mapa`, `largura`, `altura`, total de POIs e candidatos vetoriais `PyMuPDF`).
      - `content[1]` (`type: "image"`): PNG Base64 da visão geral do mapa com grade métrica `100px`, réguas `X`/`Y` e POIs em vermelho.
      - Para cada POI `i`:
        - `content[2*i + 2]` (`type: "text"`): `"POI #{i+1} | uid={poi.uid} | rotulo='{poi.rotulo}' | tipo={poi.tipo} | centro=({cx}, {cy}) | geometria={...}"`
        - `content[2*i + 3]` (`type: "image"`): PNG Base64 do recorte centrado em `(cx, cy)` com mira `(0,0)` e réguas relativas `-50px..+50px`.

## Risks / Trade-offs

- **[Risco] Payloads grandes de imagens no retorno de `aresta_renderizar_mapa` em mapas com muitos POIs** → **Mitigação**: Adicionar parâmetro opcional `incluir_recortes: bool = True` e `uids_pois: list[str] | None = None` em `aresta_renderizar_mapa`, além de comprimir os recortes (`240x240px`) de forma enxuta, permitindo que o agente filtre apenas os POIs que deseja refinar caso o mapa tenha dezenas de pontos.
- **[Risco] Concorrência em operações Git ao importar dois croquis oficiais ao mesmo tempo** → **Mitigação**: Proteger as rotinas de `git fetch`/`git worktree` em `GerenciadorGit` com um arquivo de lock (`git_operacao.lock`), serializando apenas o acesso ao repositório Git local.
- **[Risco] Subagentes tentarem editar arquivos `.md` ou `.yaml` por hábito** → **Mitigação**: Reescrever todas as skills e workflows removendo qualquer menção a formato de arquivo `.md`/`croqui.yaml` e adicionando regra explícita de proibição de escrita direta no disco.
