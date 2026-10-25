# Servidor MCP Integrado ao Editor Aresta (`editor.mcp`)

O **Editor Aresta** possui um servidor **Model Context Protocol (MCP)** integrado diretamente ao processo da aplicação desktop, permitindo que agentes autônomos e assistentes de IA (**Google Antigravity**, **OpenAI Codex**, **Claude Desktop**, **Cursor**, entre outros) inspecionem a árvore do croqui, capturem imagens em tempo real dos viewports gráficos e executem edições rastreáveis na pilha de histórico (`Undo/Redo`).

---

## 1. Arquitetura e Garantias

1. **Transporte Híbrido (HTTP/SSE + Ponte `stdio`)**:
   - O editor inicia um servidor JSON-RPC 2.0 sobre FastAPI/Uvicorn restrito a loopback (`127.0.0.1`) na porta padrão **`27378`** (mnemônico T9 para `A-R-E-S-T`), com fallback automático para portas livres caso a porta inicial esteja ocupada.
   - Os metadados da sessão ativa (`porta`, `pid`, `token`, `url_http` e `url_sse`) são gravados automaticamente em `obter_diretorio_base_app() / "mcp_sessao.json"`.
   - Para agentes que operam lançando subprocessos locais via `stdio`, o módulo `python -m editor.mcp.bridge` descobre automaticamente a porta ativa em `mcp_sessao.json` (ou via variável de ambiente `ARESTA_MCP_PORTA`) e encaminha as mensagens JSON-RPC bidirecionalmente para o editor aberto.
2. **Despacho Thread-Safe (`DespachanteQt`)**:
   - Todas as chamadas de ferramentas e leituras de recursos recebidas na thread do servidor HTTP são enfileiradas e executadas de forma síncrona na **thread principal da GUI Qt** (`PySide6`), prevenindo condições de corrida com a árvore Protobuf e com os widgets visuais.
3. **Rastreabilidade Total no Histórico (`QUndoStack`)**:
   - Toda ferramenta de mutação despacha exclusivamente através de `CroquiController` e `MapasController`, empilhando comandos `ComandoEditor` (`QUndoCommand`) auditáveis e reversíveis com `Ctrl+Z` / `Ctrl+Y` ou via ferramentas `aresta_desfazer` / `aresta_refazer`.

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
   - Exemplo: `""` (raiz do `Croqui`), `"picos.0"`, `"picos.0.setores_ou_grupos.0.setor.conteudo"`.

---

## 3. Como Conectar Seu Agente de IA

Na barra superior do **Editor Aresta**, clique no botão **`Conectar Agente de IA (MCP)...`**:
- Para **Google Antigravity**, **OpenAI Codex** e **Cursor**, o diálogo exibe um **prompt pronto** e um botão **`Copiar`** abaixo: basta colar o prompt no chat do seu agente e ele próprio atualizará seu arquivo de configuração local (funcionando inclusive quando o Editor Aresta está em sandbox MSIX ou Flatpak).
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

### 4.1. Mutação de Dados, Mapas e Macros (`editor.mcp.ferramentas_comandos`)

| Ferramenta | Descrição |
| :--- | :--- |
| `aresta_alterar_primitivo` | Altera um campo escalar (`string`, `int`, `float`, `bool`, `enum`) em uma mensagem alvo por `UID` ou caminho. |
| `aresta_alterar_oneof` | Troca a variante ativa de um grupo `oneof` (ex: `tipo` em `Escalada`) com valores iniciais opcionais. |
| `aresta_adicionar_repeated` | Insere um novo item em uma lista `repeated`, gerando e retornando imediatamente o `uid` NanoID. |
| `aresta_remover_repeated` | Remove um item de uma lista `repeated` pelo índice. |
| `aresta_mover_repeated` | Reordena um item dentro de uma lista `repeated` (`indice_origem` -> `indice_destino`). |
| `aresta_alterar_item_repeated` | Substitui o valor de um item escalar em uma lista `repeated`. |
| `aresta_alterar_multiplos_repeated` | Atualiza múltiplos itens de uma lista `repeated` em um único comando atômico. |
| `aresta_renomear_escalada` | Renomeia uma escalada atualizando referências associadas. |
| `aresta_migrar_setor` | Migra um setor para grupo ou vice-versa preservando seu conteúdo. |
| `aresta_alterar_campo_imagem` | Define ou remove a imagem associada a um campo do croqui (via Base64 ou caminho no disco). |
| `aresta_inserir_imagem_markdown` | Copia uma imagem para a pasta do croqui e insere a tag Markdown no campo de texto. |
| `aresta_inserir_botao_markdown` | Cria um `Botao` na raiz do croqui e insere a tag `<botao id="...">` no texto Markdown. |
| `aresta_adicionar_mapa_arquivo` | Cria um novo `Mapa` com arquivo de imagem em `mapas/` no container alvo. |
| `aresta_vincular_referencia_mapa` | Vincula os pontos (`pontos_uids`) de uma escalada ou setor (`alvo_uid`) em um `Mapa`. |
| `aresta_iniciar_macro` | Inicia um grupo transacional (`CmdMacro`) na pilha de histórico. |
| `aresta_finalizar_macro` | Finaliza o grupo transacional ativo, consolidando as edições em um único passo de `Undo`. |

### 4.2. Visão Multimodal e Inspeção (`editor.mcp.ferramentas_visao`)

| Ferramenta / Recurso | Descrição |
| :--- | :--- |
| `aresta_capturar_canvas` | Captura um screenshot PNG Base64 do viewport solicitado (`mapas`, `imagens`, `dados` ou `janela`). |
| `aresta_obter_arvore` | Retorna a estrutura JSON completa (ou subárvore) do croqui e o índice de `UID`s com caminhos formatados (`Grupo > Setor > Escalada`). |
| `aresta_obter_selecao_atual` | Retorna a página ativa e o elemento atualmente selecionado pelo usuário na interface gráfica. |
| `aresta://croqui/arvore` | Recurso MCP (`resources/read`) com o JSON completo do croqui e índice de `UID`s. |

### 4.3. Ciclo de Vida e Workspace (`editor.mcp.ferramentas_ciclo_vida`)

| Ferramenta | Descrição |
| :--- | :--- |
| `aresta_compilar` | Extrai os arquivos em RAM, executa a compilação/validação do croqui e retorna a lista de erros ou avisos. |
| `aresta_salvar` | Salva e compila o croqui no disco através do pipeline unificado do workspace e marca o histórico como limpo. |
| `aresta_desfazer` | Desfaz o último comando ou macro na pilha de histórico (`Undo`). |
| `aresta_refazer` | Refaz o último comando desfeito na pilha de histórico (`Redo`). |
| `aresta_focar_elemento` | Navega e destaca visualmente na interface do editor o elemento identificado por `UID` ou caminho. |
| `aresta_status_workspace` | Retorna o estado atual do croqui, caminho do banco de dados, estado `sujo` (`dirty`) e contadores de `Undo/Redo`. |
