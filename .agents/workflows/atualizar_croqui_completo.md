---
description: Orquestrador completo para atualização de um croqui existente para uma nova versão de PDF 100% via MCP
---

Este workflow atua como o **Agente Orquestrador** para atualizar um croqui já existente (oficial de produção ou rascunho local) a partir de uma nova edição do PDF, operando **100% via ferramentas MCP do Editor Aresta (`editor-aresta`)** e preservando rigorosamente todos os identificadores públicos permanentes (`uid`, `alvo_uid` e `pontos_uids`).

> [!IMPORTANT]
> **Arquitetura 100% MCP e Preservação de `UID`s:**
> - Você é o orquestrador. Delegue a leitura detalhada das páginas e mapas aos subagentes especializados.
> - **Proibição Absoluta de Edição Manual de Arquivos:** Nunca renomeie pastas manualmente no terminal nem edite arquivos `.md`, `croqui.yaml` ou `.json` diretamente no disco.
> - **Preservação Obrigatória de `UID`s:** Entidades já existentes possuem links permanentes (`aresta.cc/<uid>`). Tanto `aresta_particionar_pdf_croqui` quanto `aresta_alterar_campo` preservam `UID`s existentes quando informados.

---

### 1. Inicialização: Definição de Subagentes

Comece o workflow declarando as 4 classes de subagentes usando `define_subagent`:

- **TypeName**: `SeparadorPDF`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@separar_croqui_pdf_em_partes` operando 100% via ferramentas MCP do `editor-aresta`.

- **TypeName**: `ConversorMarkdown`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@converter_parte_croqui_para_markdown`. Inspecione primeiro o estado atual da parte com `aresta_obter_arvore`, compare com o novo sub-PDF da parte e atualize via `aresta_alterar_campo` preservando estritamente todos os `uid`, `alvo_uid` e `pontos_uids` existentes.

- **TypeName**: `CompiladorCroqui`
  - **SystemPrompt**: Siga rigorosamente as instruções da skill `@preencher_croqui_yaml` para validar metadados, executar `aresta_compilar` até atingir zero erros e zero avisos e persistir com `aresta_salvar`.

- **TypeName**: `ExtratorMapas`
  - **SystemPrompt**: Utilize em conjunto as skills `@mapa_extrair_pontos_de_interesse` e `@mapa_corrigir_pontos_de_interesse`, usando `aresta_renderizar_mapa` para verificar se os POIs existentes continuam alinhados na nova imagem ou se precisam de ajuste/adição via `aresta_alterar_campo` e `aresta_vincular_referencia_mapa`, preservando os `uid`s dos POIs existentes.

> [!NOTE]
> Ao invocar subagentes com `invoke_subagent`, utilize `Workspace: 'inherit'`.

---

### 2. Auto-Correção (Auto-Heal)

Caso algum subagente reporte falha:
1. Isole a falha sem repetir partes que já concluíram com sucesso.
2. Re-invoque (`invoke_subagent`) apenas o subagente que falhou passando o erro anterior no `Prompt`.
3. Permita até **3 retentativas** por item falho; se persistir, pause e reporte ao usuário.

---

### Fase 1: Abertura/Importação do Croqui Existente e Particionamento do Novo PDF via MCP

1. Chame `aresta_listar_croquis` para localizar o croqui que será atualizado:
   - Se for um croqui oficial de produção que ainda não possui rascunho aberto, chame `aresta_importar_croqui_oficial(id_oficial="<id_oficial>")`.
   - Se já for um rascunho em andamento ou pasta local em `database/<id_croqui>`, chame `aresta_abrir_croqui_existente(identificador="<identificador>")`.
   - Anote o `id_croqui` retornado.
2. Invoque o subagente `SeparadorPDF` passando o `id_croqui` já aberto e o caminho do **novo PDF**.
   - O `SeparadorPDF` inspecionará o novo PDF com `view_file`/`read_file` e chamará `aresta_particionar_pdf_croqui(caminho_pdf=..., partes=..., id_croqui=id_croqui)`.
   - Como o croqui já está carregado em memória, `aresta_particionar_pdf_croqui` reaproveitará automaticamente os `Setor`, `Grupo`, `Botao` e `ColecaoDeMapas` já existentes (preservando seus `UID`s originais) e pré-alocará novos esqueletos apenas para setores/apêndices inéditos da nova edição.
3. **[Checkpoint]**:
   - Pergunte ao usuário: *"O croqui `<id_croqui>` foi carregado e o novo PDF foi particionado preservando os UIDs existentes. Posso prosseguir com a Fase 2 (Atualização e Diffing Paralelo das Partes via MCP)?"*

---

### Fase 2: Atualização e Diffing Paralelo na Árvore Protobuf (Preservando `UID`s)

1. Para cada parte retornada no dicionário `partes` da Fase 1, dispare um subagente `ConversorMarkdown` em **paralelo** via `invoke_subagent`, passando `id_croqui`, `nome_parte`, `uid`, `caminho_pdf` e `imagens`.
   - No `Prompt` de cada subagente, instrua explicitamente:
     *"Consulte primeiro o estado atual da sua parte chamando `aresta_obter_arvore(alvo='<uid>', id_croqui='<id_croqui>')` e compare com o novo sub-PDF (`<caminho_pdf>`). Se o conteúdo textual, as escaladas e os mapas permanecerem equivalentes, não faça mutações e responda 'Nenhuma mudança necessária'. Caso haja novas vias, mudanças de grau/texto ou novas imagens de mapa, envie a atualização completa em uma única chamada atômica `aresta_alterar_campo(alvo='<uid>', campos={...}, id_croqui='<id_croqui>')`, PRESERVANDO OBRIGATORIAMENTE todos os campos `uid`, `alvo_uid` e `pontos_uids` das entidades que já existiam. Para novas escaladas adicionadas, omita o campo `uid`."*
2. Aguarde o retorno de todos os subagentes e aplique **Auto-Correção** se necessário.
3. Invoque o subagente `CompiladorCroqui` com `id_croqui` para executar `aresta_compilar` (corrigindo eventuais erros ou avisos) e salvar com `aresta_salvar`.
4. **[Checkpoint]**:
   - Pause e pergunte ao usuário: *"Os setores e textos foram atualizados, compilados e salvos no Editor Aresta (`<id_croqui>`). Posso prosseguir com a Fase 3 (Verificação e Atualização dos Mapas via MCP)?"*

---

### Fase 3: Verificação e Re-Extração de Mapas via `aresta_renderizar_mapa`

1. Liste os mapas do croqui via `aresta_obter_arvore(alvo="", id_croqui=id_croqui)` e agrupe-os em lotes de **no máximo 8 mapas por subagente**.
2. Dispare subagentes `ExtratorMapas` em paralelo passando `id_croqui` e a lista de `alvo_mapa` do lote:
   - Cada subagente deve chamar `aresta_renderizar_mapa(alvo=alvo_mapa, incluir_recortes=True, id_croqui=id_croqui)`.
   - Se o mapa já possuía POIs e os recortes com mira `(0, 0)` mostrarem que todos os POIs continuam perfeitamente alinhados e nenhuma nova via foi adicionada ao mapa, o subagente responde `"Nenhuma mudança necessária"` para aquele mapa.
   - Caso o mapa seja novo, tenha sofrido deslocamento/reenquadramento ou possua novas vias, o subagente extrai/ajusta as coordenadas usando a grade métrica de `100px` e os recortes relativos `-50px..+50px`, atualiza `pontos_de_interesse` via `aresta_alterar_campo` (preservando os `uid`s dos POIs preexistentes) e atualiza as `referencias` via `aresta_vincular_referencia_mapa`.
3. Aguarde a conclusão de todos os lotes e invoque `CompiladorCroqui` (`aresta_compilar` + `aresta_salvar`).
4. **[Conclusão]**:
   - Comunique ao usuário que a atualização do croqui foi concluída, compilada sem erros/avisos e salva no **Editor Aresta**.
