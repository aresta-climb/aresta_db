---
description: Orquestrador completo para conversão de croqui em formato PDF para dado estruturado 100% via MCP
---

Este workflow atua como o **Agente Orquestrador** para a conversão completa de um croqui em PDF diretamente para a árvore Protobuf do **Editor Aresta** via servidor MCP (`editor-aresta`).

> [!IMPORTANT]
> **Arquitetura 100% MCP e Ação Orquestrada:**
> - Você é o orquestrador. Nunca leia o PDF inteiro de capa a capa sozinho quando houver muitas páginas; delegue o trabalho pesado aos subagentes especializados.
> - **Proibição Absoluta de Edição Manual de Arquivos:** Nem você nem os subagentes devem criar ou editar manualmente arquivos `.md`, `croqui.yaml`, `partes.json` ou `raw_mapas/*.json` no disco, nem rodar scripts legados de terminal. Toda interação com o croqui ocorre exclusivamente via ferramentas MCP do `editor-aresta`.
> - O Editor Aresta já expõe o servidor MCP desde a Tela de Carregamento e suporta múltiplas janelas abertas em paralelo identificadas por `id_croqui`. Sempre repasse o `id_croqui` para todos os subagentes.

---

### 1. Inicialização: Definição de Subagentes

Comece o workflow declarando as 4 classes de subagentes usando `define_subagent`:

- **TypeName**: `SeparadorPDF`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@separar_croqui_pdf_em_partes` operando 100% via ferramentas MCP do `editor-aresta`.

- **TypeName**: `ConversorMarkdown`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@converter_parte_croqui_para_markdown`. Opere exclusivamente via MCP sobre o `uid` atribuído à sua parte em uma única chamada atômica `aresta_alterar_campo`, sem tocar em arquivos no disco e sem chamar `aresta_salvar`.

- **TypeName**: `CompiladorCroqui`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@preencher_croqui_yaml` para validar metadados, executar `aresta_compilar` até atingir zero erros e zero avisos e persistir com `aresta_salvar`.

- **TypeName**: `ExtratorMapas`
  - **SystemPrompt**: Utilize em conjunto as skills `@mapa_extrair_pontos_de_interesse` e `@mapa_corrigir_pontos_de_interesse`, operando exclusivamente via `aresta_renderizar_mapa`, `aresta_alterar_campo` e `aresta_vincular_referencia_mapa`.

> [!NOTE]
> Ao invocar subagentes com `invoke_subagent`, utilize `Workspace: 'inherit'` para que todos se comuniquem com a mesma sessão do Editor Aresta.

---

### 2. Auto-Correção (Auto-Heal)

Caso algum subagente reporte falha ou erro de validação:
1. Isole a falha (partes ou mapas já concluídos com sucesso não devem ser refeitos).
2. Re-invoque (`invoke_subagent`) apenas o subagente da parte/lote que falhou, incluindo no `Prompt` o erro ocorrido na tentativa anterior e instruindo-o sobre como corrigi-lo via MCP.
3. Permita até **3 retentativas** por item falho. Se ainda falhar na 3ª tentativa, aguarde os demais subagentes em andamento terminarem, pause e informe o usuário detalhando o `uid` e o erro para revisão.

---

### 3. Verificação de Estado Inicial via MCP

Antes de iniciar, chame `aresta_listar_croquis` para verificar se o croqui desejado já está aberto (`abertos`) ou em andamento (`em_andamento`):
- Se você recebeu um arquivo PDF para iniciar a conversão ou se o croqui ainda não foi particionado, comece na **Fase 1**.
- Se o croqui já está aberto/em andamento com os esqueletos criados, mas os setores/apêndices ainda estão vazios na árvore (`aresta_obter_arvore`), avance para a **Fase 2**.
- Se os setores e escaladas já estão preenchidos e compilados, mas os mapas ainda não possuem `pontos_de_interesse`, avance para a **Fase 3**.

---

### Fase 1: Abertura/Criação do Croqui e Particionamento do PDF via MCP

1. Invoque um único subagente `SeparadorPDF` passando o caminho absoluto do arquivo PDF.
   - O `SeparadorPDF` inspecionará o PDF com `view_file`/`read_file`, identificará país, estado, cidade e nome do pico, criará ou abrirá o croqui no Editor Aresta (`aresta_criar_novo_croqui` ou `aresta_abrir_croqui_existente`) e executará `aresta_particionar_pdf_croqui`.
   - Ele retornará o `id_croqui`, o `caminho_database` e o dicionário estruturado `partes` (contendo `uid`, `tipo`, `caminho_pdf` e `imagens` de cada parte pré-alocada na árvore Protobuf).
2. **[Checkpoint - Inspeção e Orientação de Imagens]**:
   - O croqui já estará aberto em uma janela do Editor Aresta.
   - Pergunte ao usuário: *"O croqui `<id_croqui>` foi criado e particionado no Editor Aresta. As partes e a orientação das imagens na aba de imagens estão corretas? Posso prosseguir com a Fase 2 (Conversão Paralela das Partes via MCP)?"*

---

### Fase 2: Conversão Paralela na Árvore Protobuf (Isolada por `UID`)

1. Para cada parte retornada no dicionário `partes` da Fase 1, dispare um subagente `ConversorMarkdown` em **paralelo** via `invoke_subagent`.
   - No `Prompt` de cada subagente, forneça explicitamente:
     - `id_croqui`: o identificador do croqui aberto;
     - `nome_parte`: a chave da parte (ex: `"capa"`, `"introducao"`, `"mapas_gerais"`, `"setor_vila"`);
     - `uid`: o `UID` exclusivo (ou caminho canônico) pré-alocado para aquela parte;
     - `caminho_pdf`: o caminho do sub-PDF daquela parte;
     - `imagens`: a lista de imagens `.webp` extraídas para aquela parte.
   - Reforce no `Prompt`: *"Opere estritamente no `alvo` igual ao seu `uid` atribuído usando uma única chamada atômica `aresta_alterar_campo`. Nunca edite arquivos no disco e nunca chame `aresta_salvar`."*
2. Aguarde a conclusão de todos os subagentes `ConversorMarkdown`. Aplique **Auto-Correção** se algum falhar.
3. Concluídas todas as partes, invoque um único subagente `CompiladorCroqui` passando o `id_croqui`.
   - Ele verificará os metadados da raiz, executará `aresta_compilar(id_croqui=id_croqui)` corrigindo eventuais erros ou avisos via MCP até zerá-los, e persistirá tudo no disco com `aresta_salvar(id_croqui=id_croqui)`.
4. **[Checkpoint]**:
   - Pause a execução e pergunte ao usuário: *"Todas as partes foram populadas, compiladas sem erros/avisos e salvas no Editor Aresta (`<id_croqui>`). Confira na janela do Editor se os setores, escaladas e imagens estão corretos. Posso prosseguir com a Fase 3 (Extração e Refinamento de Mapas via MCP)?"*

---

### Fase 3: Extração e Refinamento Visual de Mapas via `aresta_renderizar_mapa`

1. Chame `aresta_obter_arvore(alvo="", id_croqui=id_croqui)` para levantar todos os mapas existentes no croqui (`mapas_gerais`, mapas de `Grupo`, mapas de `Setor` e `escaladas[].mapas`), anotando o endereço `alvo_mapa` de cada um (ex: `"<uid_setor>.mapas.0"`) e a lista de escaladas (`uid` e `nome`) do respectivo setor.
2. Divida os mapas em lotes de **no máximo 8 mapas por subagente** e dispare subagentes `ExtratorMapas` em paralelo via `invoke_subagent`.
   - Cada subagente `ExtratorMapas` utilizará `aresta_renderizar_mapa` (aproveitando candidatos vetoriais `PyMuPDF`, a grade métrica de `100px` com réguas nas bordas e os recortes `120x120px` com mira relativa `-50px..+50px`), gravará os `pontos_de_interesse` com `aresta_alterar_campo`, vinculará as `referencias` com `aresta_vincular_referencia_mapa` e iterará visualmente até que todos os POIs estejam perfeitamente enquadrados.
3. Aguarde todos os subagentes `ExtratorMapas` terminarem (aplicando **Auto-Correção** se necessário).
4. Invoque novamente o subagente `CompiladorCroqui` passando o `id_croqui` para rodar `aresta_compilar` (garantindo zero erros e zero avisos após a adição dos POIs e referências) e salvar definitivamente com `aresta_salvar`.
5. **[Conclusão]**:
   - Comunique ao usuário que o pipeline 100% MCP foi concluído com sucesso e que o croqui já está compilado, salvo e disponível na janela aberta do **Editor Aresta** para revisão final.
