---
name: preencher_croqui_yaml
description: Valida, sanea referências, compila e salva o croqui no Editor Aresta via ferramentas MCP até que não existam erros ou avisos.
---

# Validação, Compilação e Salvamento do Croqui (100% via MCP)

Sua missão é inspecionar a árvore completa do croqui no **Editor Aresta**, garantir que todos os metadados obrigatórios e vínculos de referência estejam íntegros, executar o loop de compilação em memória via `aresta_compilar` até atingir **ZERO erros e ZERO avisos**, e persistir o projeto no disco com `aresta_salvar`.

> [!CAUTION]
> **Proibição Absoluta de Edição Manual de `croqui.yaml` ou `.md`:**
> - **NUNCA** crie ou edite manualmente o arquivo `croqui.yaml` ou arquivos `.md` no disco (`write_file`, `edit_file`) nem execute scripts de terminal legados (`deploy_generated.py`, `verificar_binarypb.py`).
> - O **Editor Aresta** gerencia a geração de `croqui.yaml`, arquivos `.md`, NanoIDs e `compilado.binarypb` diretamente a partir da árvore Protobuf em memória através de `aresta_compilar` e `aresta_salvar`.

---

## 1. Inspeção e Saneamento dos Metadados Raiz

Receba o `id_croqui` do Agente Orquestrador e execute a verificação inicial:

1. Chame `aresta_status_workspace(id_croqui=id_croqui)` e `aresta_obter_arvore(alvo="", id_croqui=id_croqui)` para inspecionar a raiz do `Croqui` e `picos[0]`.
2. Verifique os campos essenciais na raiz (`alvo=""`) e no pico (`alvo="picos[0]"`):
   - **`caminho_thumbnail`**: Deve apontar para a imagem de capa ou para uma imagem representativa do croqui na pasta `imagens/`. Se estiver vazio, defina-o com `aresta_alterar_campo(alvo="", campo="caminho_thumbnail", valor="imagens/...", id_croqui=id_croqui)`.
   - **`ultima_migracao`**: O Editor Aresta já gerencia a versão de migração automaticamente, mas se estiver zerada, garanta que esteja definida com a migração atual (`5`).
   - **Proibição de tocar em `revisado_*`**: **NUNCA** altere ou marque como `true` os campos `revisado_*`, pois são exclusivos para revisão humana na interface gráfica.
   - **Vínculo de Referências em Mapas (`referencias`)**: Quando os mapas dos setores/grupos já possuírem `pontos_de_interesse` extraídos, verifique se as `referencias` do mapa vinculam cada escalada/setor (`alvo_uid`) aos respectivos pontos (`pontos_uids`) usando `aresta_vincular_referencia_mapa` ou `aresta_alterar_campo`. Se algum ponto no mapa tiver exatamente o mesmo rótulo/número correspondente à ordem ou nome de uma escalada do setor e ainda não estiver vinculado em `referencias`, crie o vínculo com `aresta_vincular_referencia_mapa`.

---

## 2. Loop de Compilação e Auto-Correção via MCP (`aresta_compilar`)

Execute a validação completa do croqui diretamente no Editor Aresta:

1. Chame `aresta_compilar(id_croqui=id_croqui)`.
2. Analise a resposta JSON (`sucesso`, `erros`, `avisos`, `total_erros`, `total_avisos`):
   - **Se houver qualquer erro ou aviso (`total_erros > 0` ou `total_avisos > 0`)**:
     - Leia atentamente cada mensagem de erro ou aviso retornada pelo compilador do Editor.
     - Use `aresta_obter_arvore` para inspecionar o elemento apontado (seja um `Setor`, `Grupo`, `Botao`, `Escalada` ou `Mapa`).
     - Corrija o problema utilizando exclusivamente as ferramentas MCP (`aresta_alterar_campo`, `aresta_remover_repeated`, `aresta_vincular_referencia_mapa`, `aresta_alterar_imagem`). Exemplos comuns:
       - Título H1 duplicado (`# Setor ...`) dentro de `introducao`: remova o H1 com `aresta_alterar_campo`.
       - Caminho de imagem inexistente ou vazio em `caminho_imagem_mapa` ou Markdown: corrija para a imagem válida em `imagens/`.
       - Escalada sem nome ou sem dificuldade válida: consulte a página correspondente e ajuste com `aresta_alterar_campo`.
       - Referência de mapa apontando para `alvo_uid` ou `pontos_uids` inexistente: atualize com `aresta_vincular_referencia_mapa` ou `aresta_alterar_campo`.
     - Chame `aresta_compilar(id_croqui=id_croqui)` novamente.
3. Repita o passo 2 até que `aresta_compilar` retorne **`sucesso: true`, `total_erros: 0` e `total_avisos: 0`**.

---

## 3. Persistência no Disco (`aresta_salvar`)

Assim que `aresta_compilar(id_croqui=id_croqui)` atingir **ZERO erros e ZERO avisos**:

1. Chame `aresta_salvar(id_croqui=id_croqui)`.
   - Esta ferramenta persiste todos os arquivos do croqui no disco (`croqui.yaml`, páginas `.md`, imagens em memória e `compilado.binarypb`) através do pipeline unificado do Editor Aresta e marca o workspace como limpo (`sujo: false`).
2. Confirme que `aresta_salvar` retornou `"sucesso": true` e reporte a conclusão ao Agente Orquestrador.

## Quando usar essa habilidade

Use essa habilidade ao final da conversão das partes ou após a extração/correção dos mapas para validar, sanear, compilar sem erros/avisos e salvar o croqui no Editor Aresta via MCP.
