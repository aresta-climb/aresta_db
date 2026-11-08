# Servidor MCP Integrado ao Editor Aresta (`editor.mcp`)

O **Editor Aresta** possui um servidor **Model Context Protocol (MCP)** integrado diretamente ao processo da aplicação desktop, permitindo que agentes autônomos e assistentes de IA (**Google Antigravity**, **OpenAI Codex**, **Claude Desktop**, **Cursor**, entre outros) gerenciem croquis desde a Tela de Carregamento, particionem arquivos PDF, inspecionem a árvore Protobuf, renderizem mapas com grade métrica e recortes de precisão e executem edições atômicas rastreáveis na pilha de histórico (`QUndoStack`).

---

## 1. Arquitetura e Garantias

1. **MCP Ativo Desde a Tela de Carregamento e Guarda Defensiva**:
   - O `ServidorMCP` é iniciado imediatamente no boot do aplicativo (`ControladorAplicativo`), ficando ativo mesmo antes de qualquer croqui ser aberto na `TelaDeCarregamento` (onde o botão **`Conectar Agente de IA (MCP)...`** já está disponível).
   - Quando **nenhum croqui está aberto**, ferramentas de gestão de croquis (`aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui`) e de conhecimento (`aresta_obter_esquema_proto`, `aresta_listar_skills`, `aresta_ler_skill`) operam normalmente, enquanto ferramentas que exigem um croqui aberto retornam imediatamente um erro descritivo orientando o agente a listar e abrir/criar um croqui primeiro.
2. **Múltiplas Janelas em Paralelo, Trava por Croqui e Roteamento Proxy (`27378`)**:
   - O Editor Aresta aplica trava de instância única **por croqui** (`ArestaEditorCroqui_<id_croqui>`), permitindo que croquis distintos sejam abertos simultaneamente em janelas independentes (e elevando a janela existente caso o mesmo croqui seja solicitado novamente).
   - Todas as sessões ativas são registradas de forma atômica em `obter_diretorio_base_app() / "mcp_sessoes.json"` (mantendo também `mcp_sessao.json` para compatibilidade).
   - O servidor primário na porta **`27378`** (mnemônico T9 para `A-R-E-S-T`) atua como roteador transparente: todas as ferramentas de croqui aceitam o parâmetro opcional `id_croqui`. Se houver apenas 1 croqui aberto, `id_croqui` é resolvido automaticamente; se houver múltiplos croquis abertos (na mesma instância ou em processos secundários nas portas `27379+`), o servidor na porta `27378` despacha localmente ou faz proxy HTTP transparente para a porta da janela correspondente ao `id_croqui`.
3. **Transporte Híbrido (HTTP/SSE + Ponte `stdio`)**:
   - O servidor JSON-RPC 2.0 roda sobre FastAPI/Uvicorn restrito a loopback (`127.0.0.1`).
   - Para agentes que operam via subprocesso `stdio`, `python -m editor.mcp.bridge` descobre automaticamente a porta ativa e encaminha as mensagens JSON-RPC bidirecionalmente.
4. **Despacho Thread-Safe (`DespachanteQt`) e Transações Atômicas no Histórico (`QUndoStack`)**:
   - Todas as chamadas são executadas de forma síncrona na **thread principal da GUI Qt** (`PySide6`), prevenindo condições de corrida.
   - `aresta_alterar_campo` suporta a substituição declarativa completa de objetos e listas `repeated` (como `escaladas`, `mapas`, `pontos_de_interesse`, `referencias`) dentro de um único `CmdMacro` atômico no `QUndoStack`, preservando `uid`s existentes e gerando NanoIDs para novos itens.
   - As ações de `Undo/Redo` não são expostas como ferramentas MCP para evitar que subagentes em paralelo desfaçam operações uns dos outros, mas permanecem 100% disponíveis para o usuário humano na interface gráfica (`Ctrl+Z` / `Ctrl+Y`).

---

## 2. Endereçamento Híbrido Ancorado em `UID`

Todas as ferramentas que recebem o parâmetro `alvo` aceitam três formatos complementares resolvidos por `resolver_alvo_mcp`:

1. **`UID` Universal (`IndiceUidsModel`)**:
   - Exemplo: `"V1StGXR8_Z5jdH"`
   - Localiza em $O(1)$ qualquer `Setor`, `Grupo`, `Escalada`, `Botao` ou `PontoDeInteresse` registrado no índice do croqui, independentemente de reordenações nas listas.
   - Em entidades com `oneof tipo` (como `Escalada` e `Enfiada`), ao alterar um campo pertencente à variante ativa (`via_esportiva`, `boulder`, etc.), o resolvedor redireciona automaticamente para o sub-objeto ativo.
2. **Sub-caminho Relativo a partir de um `UID`**:
   - Exemplo: `"V1StGXR8_Z5jdH.mapas.0"` ou `"V1StGXR8_Z5jdH.enfiadas.0"`
   - Resolve a entidade base pelo `UID` e navega pelo sub-caminho relativo.
3. **Caminho Posicional desde a Raiz**:
   - Exemplo: `""` (raiz do `Croqui`), `"picos.0"`, `"picos[0].mapas_gerais.conteudo"`.

---

## 3. Como Conectar Seu Agente de IA

Tanto na **Tela de Carregamento** quanto na barra superior da **Janela Principal** do **Editor Aresta**, clique no botão **`Conectar Agente de IA (MCP)...`**:
- Para **Google Antigravity**, **OpenAI Codex** e **Cursor**, o diálogo exibe um **prompt pronto** e um botão **`Copiar`** abaixo: basta colar o prompt no chat do seu agente e ele próprio atualizará seu arquivo de configuração local.
- Para **Claude Desktop**, o diálogo exibe o passo a passo para abrir o `claude_desktop_config.json` (`Settings > Developer > Edit Config`) e colar o bloco JSON.

### 3.1. Google Antigravity (`~/.gemini/antigravity/mcp_config.json`)

```json
{
  "mcpServers": {
    "editor-aresta": {
      "serverUrl": "http://127.0.0.1:27378/mcp"
    }
  }
}
```

### 3.2. OpenAI Codex (`~/.codex/config.toml`)

```toml
[mcp_servers.editor-aresta]
url = "http://127.0.0.1:27378/mcp"
```

### 3.3. Claude Desktop (`claude_desktop_config.json`)

1. No Claude Desktop, abra **Configurações (Settings) > Desenvolvedor (Developer) > Editar Configuração (Edit Config)**.
2. Insira o bloco abaixo dentro de `"mcpServers"`, salve e reinicie o Claude Desktop:

```json
{
  "mcpServers": {
    "editor-aresta": {
      "command": "uv",
      "args": ["run", "python", "-m", "editor.mcp.bridge"]
    }
  }
}
```

### 3.4. Cursor (`~/.cursor/mcp.json` ou `.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "editor-aresta": {
      "url": "http://127.0.0.1:27378/mcp"
    }
  }
}
```

---

## 4. Catálogo de Ferramentas MCP

### 4.1. Gestão de Croquis e Pipeline PDF (`editor.mcp.ferramentas_ciclo_vida`)

| Ferramenta | Requer Croqui Aberto? | Descrição |
| :--- | :---: | :--- |
| `aresta_listar_croquis` | Não | Lista croquis `abertos` nas janelas ativas, rascunhos locais `em_andamento` e croquis `oficiais` de produção (com filtro opcional `busca`). |
| `aresta_abrir_croqui_existente` | Não | Abre um croqui em andamento (`<id>_<timestamp>`) ou pasta local `database/<id_croqui>` na janela atual (se na Tela de Carregamento) ou em nova janela independente. |
| `aresta_importar_croqui_oficial` | Não | Clona um croqui oficial de produção para edição experimental, compila e o abre no Editor. |
| `aresta_criar_novo_croqui` | Não | Cria a estrutura inicial de um novo croqui a partir de `nome_pico`, `cidade`, `estado` e `pais`, compila e o abre no Editor. |
| `aresta_particionar_pdf_croqui` | Sim | Fatia um PDF em sub-PDFs por parte (`PyMuPDF`), extrai imagens `.webp` para `imagens/`, extrai candidatos vetoriais (`*_dados.json`) e pré-aloca os esqueletos (`Setor`, `Grupo`, `Botao`, `ColecaoDeMapas`) na árvore Protobuf preservando `UID`s existentes. |

### 4.2. Mutação de Dados e Mapas (`editor.mcp.ferramentas_comandos`)

| Ferramenta | Descrição |
| :--- | :--- |
| `aresta_alterar_campo` | Altera um campo (`campo` + `valor`) ou múltiplos campos em lote atômico (`campos: dict`) em uma mensagem alvo por `UID` ou caminho, incluindo **substituição declarativa completa de listas `repeated`** (`escaladas`, `mapas`, `pontos_de_interesse`, `referencias`) dentro de um único `CmdMacro` (preservando `uid`s fornecidos e gerando NanoIDs para novos itens). |
| `aresta_adicionar_repeated` | Insere um ou mais itens (`valores`, escalares ou `dict`s JSON) ao final ou em uma posição específica de uma lista `repeated`, retornando os `uids` NanoID gerados e o `tamanho` atualizado. |
| `aresta_remover_repeated` | Remove um item de uma lista `repeated` pelo índice e retorna o `tamanho` atualizado. |
| `aresta_mover_repeated` | Reordena um item dentro de uma lista `repeated` (`indice_origem` -> `indice_destino`). |
| `aresta_migrar_setor` | Migra um setor para grupo ou vice-versa preservando seu conteúdo. |
| `aresta_alterar_imagem` | Define ou remove a imagem associada a um campo do croqui (via Base64 ou caminho no disco). |
| `aresta_alterar_campo_imagem` | Altera metadados (`autor`, `data`) de um `ArquivoImagem` registrado no croqui. |
| `aresta_inserir_imagem_markdown` | Copia uma imagem para a pasta do croqui e insere a tag Markdown no campo de texto. |
| `aresta_inserir_botao_markdown` | Cria um `Botao` na raiz do croqui e insere a tag `<botao id="...">` no texto Markdown. |
| `aresta_adicionar_mapa_arquivo` | Cria um novo `Mapa` com arquivo de imagem no container alvo (`Setor`, `Grupo`, `Escalada` ou `ColecaoDeMapas`). |
| `aresta_vincular_referencia_mapa` | Vincula os pontos (`pontos_uids`) de uma escalada ou setor (`alvo_uid`) na lista `referencias` de um `Mapa`. |

### 4.3. Visão Multimodal, Renderização de Mapas e Inspeção (`editor.mcp.ferramentas_visao`)

| Ferramenta / Recurso | Descrição |
| :--- | :--- |
| `aresta_renderizar_mapa` | Renderiza um `Mapa` retornando uma sequência intercalada de blocos `[Texto, Imagem]`: **(1)** Metadados do mapa (`largura`, `altura`, POIs atuais e candidatos vetoriais extraídos via `PyMuPDF`) + Imagem completa do mapa com grade métrica semitransparente (`100px`), réguas graduadas nas bordas (`X`/`Y`) e POIs em vermelho; **(2)** Pares `[Texto, Imagem]` para cada POI com recorte ampliado (`120x120px` escalado para `240x240px`) centrado no POI com mira `(0, 0)` e réguas relativas de `-50px` a `+50px`. |
| `aresta_capturar_canvas` | Captura um screenshot PNG Base64 do viewport solicitado (`mapas`, `imagens`, `dados` ou `janela`). |
| `aresta_obter_arvore` | Retorna a estrutura JSON completa (ou subárvore/campo filtrado por `alvo` e `campo`), `tamanhos_repeated` com a contagem de itens das listas da mensagem e o índice de `UID`s na raiz. |
| `aresta_obter_selecao_atual` | Retorna a página ativa e o elemento atualmente selecionado pelo usuário na interface gráfica. |
| `aresta://croqui/arvore` | Recurso MCP (`resources/read`) com o JSON completo do croqui, `tamanhos_repeated` e índice de `UID`s. |

### 4.4. Descoberta de Esquema Protobuf e Skills (`editor.mcp.ferramentas_conhecimento`)

| Ferramenta / Recurso | Descrição |
| :--- | :--- |
| `aresta_obter_esquema_proto` | Retorna a definição estruturada de `croqui.proto` (campos, tipos, `oneofs`, valores de `Enum`, comentários) ou a visão geral com guia de uso MCP. |
| `aresta_listar_skills` | Lista todas as skills de domínio em `.agents/skills/` com nome e descrição. |
| `aresta_ler_skill` | Lê o conteúdo completo (`SKILL.md`) e lista os arquivos auxiliares de uma skill específica. |
| `aresta://esquema/proto` | Recurso MCP (`resources/read`) com o esquema e guia rápido de `croqui.proto`. |
| `aresta://skills` | Recurso MCP (`resources/read`) com o catálogo de skills disponíveis. |

### 4.5. Compilação, Salvamento e Navegação (`editor.mcp.ferramentas_ciclo_vida`)

| Ferramenta | Descrição |
| :--- | :--- |
| `aresta_compilar` | Extrai os arquivos em RAM, executa a compilação/validação do croqui e retorna a lista de erros ou avisos. |
| `aresta_salvar` | Salva e compila o croqui no disco através do pipeline unificado do workspace e marca o histórico como limpo. |
| `aresta_focar_elemento` | Navega e destaca visualmente na interface do editor o elemento identificado por `UID` ou caminho. |
| `aresta_status_workspace` | Retorna o estado atual do croqui, `id_croqui`, caminho do banco de dados, estado `sujo` (`dirty`) e contadores de `Undo/Redo`. |
