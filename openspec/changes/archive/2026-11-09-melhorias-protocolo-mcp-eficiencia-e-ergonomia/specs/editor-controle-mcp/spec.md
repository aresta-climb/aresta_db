# editor-controle-mcp Spec Delta

## ADDED Requirements

### Requirement: Omissão de Extensões e Campos Protobuf Invisíveis na Árvore e no Esquema MCP
As ferramentas `aresta_obter_arvore` e `aresta_obter_esquema_proto` MUST omitir chaves de extensão Protobuf iniciadas por `"[aresta."` (como `ext_metadados_arquivo`) e todos os campos marcados no `croqui.proto` com `(aresta.formato_na_ui) = INVISIVEL` ou `(aresta.mensagem_formato_na_ui) = INVISIVEL`, preservando visíveis exclusivamente os identificadores de endereçamento `uid`, `alvo_uid` e `pontos_uids`.

#### Scenario: Omissão de ext_metadados_arquivo e campos INVISIVEL em aresta_obter_arvore preservando UIDs
- **WHEN** o cliente MCP chama `aresta_obter_arvore` em um croqui contendo extensões `[aresta.ArquivoSetor.ext_metadados_arquivo]`, campos `precomputados`, `malha_estrada`, `arquivos_externos`, `ultima_migracao`, `curadoria_betas`, `compilado` e campos legados de referência (`id`, `ids`, `escalada`, `setor`, `grupo`)
- **THEN** o dicionário retornado em `dados` e `tamanhos_repeated` omite recursivamente todas essas chaves e extensões, mas preserva integralmente os campos `uid`, `alvo_uid` e `pontos_uids` em todas as mensagens

#### Scenario: Omissão de campos e tipos INVISIVEL em aresta_obter_esquema_proto preservando UIDs
- **WHEN** o cliente MCP chama `aresta_obter_esquema_proto` (com ou sem `tipo_mensagem`)
- **THEN** a definição estruturada das mensagens omite os campos internos/depreciados marcados como `INVISIVEL` (como `precomputados`, `malha_estrada`, `compilado` e campos legados de `Referencia`), mantendo documentados os campos `uid`, `alvo_uid` e `pontos_uids`

### Requirement: Listagem Tabular de Escaladas Cruzadas com Referências de Mapas
O servidor MCP MUST disponibilizar a ferramenta `aresta_listar_escaladas` (aceitando `alvo_setor` e `filtro_nome` opcionais) que percorre setores, grupos e mapas do croqui (incluindo `mapas_gerais`) e retorna uma lista compacta das escaladas enriquecida com `uid`, `indice_no_setor`, `setor_uid`, `setor_nome`, `rotulos_mapa`, `pontos_uids`, `tipo`, `nome`, `dificuldade`, `data_abertura` e `conquistadores`.

#### Scenario: Listagem de todas as escaladas do croqui com rótulos de mapa resolvidos
- **WHEN** o cliente MCP chama `aresta_listar_escaladas` sem filtros (ou filtrando por `alvo_setor` / `filtro_nome`)
- **THEN** o servidor cruza os `alvo_uid` das `referencias` de todos os mapas dos setores e de `mapas_gerais` com os `pontos_de_interesse` correspondentes e retorna a lista de escaladas contendo seus respectivos `rotulos_mapa` e `pontos_uids`

### Requirement: Inserção em Lote e Retorno Explícito de UIDs Gerados em Coleções Repeated
A ferramenta `aresta_adicionar_repeated` MUST aceitar tanto `valor` (item único) quanto `valores` (lista de itens inseridos atomicamente em um único `CmdMacro`) e MUST retornar explicitamente os campos `uid`, `uid_gerado` (quando 1 item for inserido) e `uids_gerados` (lista com os UIDs gerados na ordem de inserção), além do índice inicial inserido e do tamanho final da coleção.

#### Scenario: Adição de item único ou múltiplos itens em lista repeated com retorno de UIDs gerados
- **WHEN** o cliente MCP chama `aresta_adicionar_repeated` passando `valor` (1 item) ou `valores` (lista de N itens) para uma coleção de mensagens com `uid` (como `escaladas` ou `pontos_de_interesse`)
- **THEN** todos os itens recebem `uid` NanoID válido, são inseridos atomicamente no `CroquiModel` (em um único passo de `undo()` quando em lote), o `IndiceUidsModel` é atualizado e o retorno JSON inclui `uids_gerados` (e `uid_gerado` quando unitário)

### Requirement: Remoção Seletiva ou Integral de Referências de Mapa via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_remover_referencia_mapa` (apoiada por `MapasController.remover_referencia`) para desvincular pontos específicos (`pontos_uids`) de uma `Referencia` de `alvo_uid` em um `Mapa` ou remover a entrada `Referencia` inteira quando `pontos_uids` for omitido ou quando todos os seus pontos forem removidos.

#### Scenario: Desvinculação seletiva de pontos ou remoção integral de referência em um mapa
- **WHEN** o cliente MCP chama `aresta_remover_referencia_mapa` informando `alvo_mapa`, `alvo_uid` e opcionalmente `pontos_uids`
- **THEN** se `pontos_uids` contiver apenas parte dos pontos vinculados ao `alvo_uid`, o sistema atualiza a `Referencia` mantendo os pontos restantes via `CmdAlterarCampo`; se `pontos_uids` for omitido ou esvaziar todos os pontos da `Referencia`, o sistema remove a entrada `Referencia` via `CmdRemoverRepeated`

### Requirement: Preservação Opt-In de Campos Compatíveis na Troca de Variante Oneof via MCP
As ferramentas `aresta_alterar_campo` e `aresta_alterar_em_lote` MUST aceitar o parâmetro booleano opcional `preservar_campos_compativeis` (padrão `False`). Quando `preservar_campos_compativeis=True` e a mutação alterar a variante ativa de um `oneof` de submensagem, o sistema MUST copiar os campos homônimos compatíveis já preenchidos da variante anterior antes de aplicar os novos valores fornecidos.

#### Scenario: Conversão de modalidade de escalada com preservar_campos_compativeis ativado
- **WHEN** uma `Escalada` do tipo `via_esportiva` (com `nome`, `dificuldade`, `conquistadores`, `data_abertura` e `descricao` preenchidos) é alterada para `via_movel` via `aresta_alterar_campo` ou `aresta_alterar_em_lote` com `preservar_campos_compativeis=True`
- **THEN** a nova submensagem `via_movel` herda automaticamente todos os campos homônimos compatíveis da `via_esportiva` anterior, sobrescrevendo apenas os campos explicitamente informados na chamada, e um único `undo()` restaura a `via_esportiva` original

#### Scenario: Conversão de modalidade de escalada com preservar_campos_compativeis padrão (False)
- **WHEN** o cliente altera a variante de um `oneof` sem informar `preservar_campos_compativeis` (ou com `preservar_campos_compativeis=False`)
- **THEN** a nova submensagem da variante contém apenas os campos explicitamente enviados na chamada, mantendo o comportamento padrão do Protobuf
