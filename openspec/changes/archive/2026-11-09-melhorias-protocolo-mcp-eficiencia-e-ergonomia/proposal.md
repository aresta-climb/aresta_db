# Proposal

## Why

Durante a revisão completa do croqui da Gruta da Lapinha via servidor MCP (`editor-aresta`), identificamos cinco gargalos no protocolo que aumentam o consumo de tokens, exigem chamadas redundantes de introspecção ou induzem a erros de manipulação de estado:
1. `aresta_obter_arvore` e `aresta_obter_esquema_proto` serializam extensões internas (`[aresta.ArquivoSetor.ext_metadados_arquivo]` com `dados_json_originais`) e campos marcados como `INVISIVEL` no `croqui.proto` (`precomputados`, `malha_estrada`, `arquivos_externos`, `ultima_migracao`, `curadoria_betas`, `compilado` e campos legados de referência), duplicando o tamanho do JSON da árvore (mais de 175 KB em um único croqui) e expondo campos depreciados ao agente.
2. Não existe uma ferramenta direta que cruze as `Escaladas` de cada setor com os `pontos_de_interesse` e `referencias` dos mapas (`rotulos_mapa` e `pontos_uids`), obrigando o agente a baixar a árvore inteira e cruzar dicionários manualmente para descobrir qual número no mapa corresponde a qual `uid` de escalada.
3. `aresta_adicionar_repeated` aceita apenas um único item por chamada (`valor`) — apesar de o guia de uso mencionar `valores` em lote — e retorna apenas `"uid"`, sem expor explicitamente `"uid_gerado"` e `"uids_gerados"` para inserções unitárias ou múltiplas.
4. `aresta_vincular_referencia_mapa` permite adicionar vínculos em `Mapa.referencias`, mas não há uma ferramenta simétrica `aresta_remover_referencia_mapa` para desvincular pontos específicos (`pontos_uids`) ou remover a entrada `Referencia` de um `alvo_uid` sem reescrever a lista inteira de referências do mapa.
5. Ao converter a modalidade (`oneof tipo`) de uma `Escalada` (ex.: de `via_esportiva` para `via_movel`), o Protobuf limpa a submensagem anterior, exigindo reenviar todos os campos comuns manualmente; além disso, erros de campo inexistente em `CmdAlterarCampo` não informam quais são os campos válidos da mensagem alvo.

## What Changes

- **Omissão eficiente ($O(1)$) de `ext_metadados_arquivo` e campos Protobuf `INVISIVEL` no MCP**:
  - Pré-computar na carga do módulo um mapa imutável `_CAMPOS_OCULTOS_MCP: dict[str, frozenset[str]]` indexado por `Descriptor.full_name` contendo todos os campos com `(aresta.formato_na_ui) == INVISIVEL` ou cuja submensagem tenha `(aresta.mensagem_formato_na_ui) == INVISIVEL`, **exceto** os identificadores de endereçamento `{"uid", "alvo_uid", "pontos_uids"}`.
  - Filtrar recursivamente em `aresta_obter_arvore` e `aresta_obter_esquema_proto` todas as chaves de extensão iniciadas por `"[aresta."` (como `ext_metadados_arquivo`) e todos os campos pertencentes a `_CAMPOS_OCULTOS_MCP`.
- **Nova ferramenta MCP `aresta_listar_escaladas` e atualização de skills**:
  - Registrar `aresta_listar_escaladas` em `editor/mcp/ferramentas_visao.py` (com parâmetros opcionais `alvo_setor` e `filtro_nome`), percorrendo setores (inclusive dentro de grupos) e mapas (incluindo `mapas_gerais` do pico) para retornar uma tabela compacta por escalada contendo `uid`, `indice_no_setor`, `setor_uid`, `setor_nome`, `rotulos_mapa`, `pontos_uids`, `tipo`, `nome`, `dificuldade`, `data_abertura` e `conquistadores`.
  - Atualizar as skills `.agents/skills/preencher_croqui_yaml/SKILL.md` e `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` para orientar o uso de `aresta_listar_escaladas` e das novas ferramentas.
- **Suporte a lote (`valores`) e retorno explícito de `uid_gerado` / `uids_gerados` em `aresta_adicionar_repeated`**:
  - Permitir que `aresta_adicionar_repeated` receba `valor` (item único) ou `valores` (lista de itens inseridos atomicamente via `CmdMacro` no `CroquiController`) e retorne no JSON `"uid"` (compatibilidade), `"uid_gerado"` (quando 1 item for inserido) e `"uids_gerados"` (lista com os UIDs gerados para todos os itens inseridos).
- **Nova ferramenta MCP `aresta_remover_referencia_mapa` (`MapasController.remover_referencia`)**:
  - Adicionar `MapasController.remover_referencia(msg_mapa_proxy, alvo_uid, pontos_uids=None)` em `editor/controllers/mapas_controller.py` e expor `aresta_remover_referencia_mapa` em `editor/mcp/ferramentas_comandos.py`.
  - Quando `pontos_uids` for omitido ou vazio, remover a entrada `Referencia` correspondente a `alvo_uid` via `CmdRemoverRepeated`; quando `pontos_uids` for informado, remover apenas aqueles UIDs de ponto da `Referencia` (via `CmdAlterarCampo`) ou remover a `Referencia` inteira (via `CmdRemoverRepeated`) caso sua lista `pontos_uids` fique vazia.
- **Preservação opt-in de campos compatíveis em troca de `oneof` (`preservar_campos_compativeis: bool = False`) e listagem de campos válidos em erros**:
  - Adicionar o parâmetro opcional `preservar_campos_compativeis: bool = False` em `CroquiController.alterar_campo`, `CroquiController.alterar_em_lote`, `aresta_alterar_campo` e `aresta_alterar_em_lote`. Quando `preservar_campos_compativeis=True` e a operação trocar a variante ativa de um `oneof` de submensagem (como `Escalada.tipo` entre `via_esportiva`, `via_movel`, `boulder`, `via_multiplas_enfiadas` e `highline`), copiar automaticamente os campos homônimos compatíveis já preenchidos da variante anterior antes de aplicar os novos valores fornecidos pelo chamador.
  - Em `validar_pertence_ao_croqui` e `_validar_campo_se_msg_existir` (`editor/commands/comandos_protobuf.py`), incluir na mensagem de `ValueError` de campo inexistente a lista ordenada de campos válidos (e `oneofs`) do `DESCRIPTOR` da mensagem alvo.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability de nível de topo é necessária; as mudanças estendem as especificações existentes abaixo. -->

### Modified Capabilities
- `editor-controle-mcp`: Especifica a omissão de extensões `[aresta.*]` e campos `INVISIVEL` (exceto `uid`, `alvo_uid` e `pontos_uids`) em `aresta_obter_arvore` e `aresta_obter_esquema_proto`, a nova ferramenta `aresta_listar_escaladas`, o retorno de `uid_gerado`/`uids_gerados` (com suporte a `valores` em lote) em `aresta_adicionar_repeated`, a nova ferramenta `aresta_remover_referencia_mapa` e a flag `preservar_campos_compativeis: bool = False` em `aresta_alterar_campo` / `aresta_alterar_em_lote`.
- `undo-redo-protobuf`: Especifica a inclusão dos campos válidos do `DESCRIPTOR` nas exceções `ValueError` de campo inexistente em `comandos_protobuf.py`, a preservação opt-in (`preservar_campos_compativeis=True`) na troca de ramo `oneof` no `CroquiController` e a remoção atômica de referências de mapa em `MapasController.remover_referencia`.

## Impact

- `editor/mcp/ferramentas_conhecimento.py` e `editor/mcp/ferramentas_conhecimento_test.py` (mapa pré-computado `_CAMPOS_OCULTOS_MCP` e filtragem em `aresta_obter_esquema_proto`).
- `editor/mcp/ferramentas_visao.py` e `editor/mcp/ferramentas_visao_test.py` (filtragem de extensões e campos invisíveis em `aresta_obter_arvore` e nova ferramenta `aresta_listar_escaladas`).
- `editor/mcp/ferramentas_comandos.py` e `editor/mcp/ferramentas_comandos_test.py` (`aresta_adicionar_repeated` com `valores`/`uid_gerado`/`uids_gerados`, `aresta_remover_referencia_mapa` e `preservar_campos_compativeis` em `aresta_alterar_campo` e `aresta_alterar_em_lote`).
- `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py` (`preservar_campos_compativeis: bool = False` na troca de `oneof` e adição de múltiplos itens repeated em macro).
- `editor/controllers/mapas_controller.py` e `editor/controllers/mapas_controller_test.py` (`MapasController.remover_referencia`).
- `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_protobuf_test.py` (listagem de campos válidos do `DESCRIPTOR` em `ValueError` de campo inexistente).
- `.agents/skills/preencher_croqui_yaml/SKILL.md` e `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`.
