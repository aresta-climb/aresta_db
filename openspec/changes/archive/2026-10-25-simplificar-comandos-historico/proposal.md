# Proposal

## Why

Atualmente, a camada de histórico (`editor/commands/`) acumula 16 classes de comandos (`QUndoCommand`) criadas incrementalmente ao longo da evolução do editor. Com a adoção consolidada de identificadores únicos universais (`UID`s NanoID via `IndiceUidsModel`) e de referências por `alvo_uid` em mapas, vários comandos tornaram-se redundantes (como `CmdRenomearEscalada`, que já não muta referências no `undo`/`redo`), fragmentados por tipo de campo (`CmdAlterarPrimitivo`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMetadadosCaminhoNovo`) ou acoplados a combinações ad-hoc de mutação Protobuf com buffers de memória RAM (`CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdAdicionarMapaArquivo`). Simplificar o núcleo de comandos para um conjunto canônico enxuto guiado por Reflection (`DESCRIPTOR`) e endereçamento por `UID` reduz drasticamente a complexidade de manutenção, melhora a ergonomia do servidor MCP e preserva 100% de retrocompatibilidade com diários locais (`diario_pendente.bin` e `diario_salvo.bin`) de croquis já em edição.

## What Changes

- **Núcleo de 7 Comandos Canônicos em `editor/commands/comandos_protobuf.py`**:
  - **`CmdAlterarCampo`**: Comando unificado guiado por Reflection (`DESCRIPTOR`) e resolução por `alvo` (`UID` direto, `<uid>.<subcaminho>` ou fallback posicional desde a raiz), substituindo `CmdAlterarPrimitivo`, `CmdRenomearEscalada`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem` e `CmdAlterarMetadadosCaminhoNovo`. Captura automaticamente o estado anterior quando omitido e suporta mesclagem contínua (`mergeWith`) delimitada por `session_id`.
  - **`CmdAdicionarRepeated`**, **`CmdRemoverRepeated`** e **`CmdMoverRepeated`**: Comandos dedicados e explícitos (uma assinatura por operação) para inserção, remoção e reordenação em coleções `repeated`, com resolução de alvo ancorada em `UID`.
  - **`CmdAlterarImagem`**: Comando atômico para adicionar, substituir ou remover bytes de imagem (`.webp`) no buffer em memória RAM do `CroquiModel` (emitindo `imagem_alterada` e suportando anonimização WebP para telemetria), substituindo `CmdSubstituirImagemMemoria`.
  - **`CmdAlterarAnexo`**: Comando atômico para adicionar, substituir ou remover bytes de documentos anexos no buffer em memória RAM do `CroquiModel`.
  - **`CmdMacro`**: Agrupador transacional atômico que compõe sequências dos comandos canônicos acima.
- **Operações de Alto Nível via Composição (`CmdMacro`) nos Controllers**:
  - As intenções compostas em `CroquiController` e `MapasController` (`migrar_setor`, `alterar_campo_imagem`, `inserir_imagem_markdown`, `inserir_botao_markdown`, `adicionar_mapa_com_arquivo`, `alterar_multiplos_repeated_items` e limpeza de imagens órfãs ao remover itens) passam a construir e empilhar instâncias de `CmdMacro` compostas exclusivamente pelos comandos canônicos, eliminando a necessidade de classes de comando específicas e do método `CroquiModel._migrar_setor`.
- **Alinhamento do Catálogo de Ferramentas MCP (`editor/mcp/ferramentas_comandos.py`)**:
  - Unificação das ferramentas de edição de campos no MCP em `aresta_alterar_campo` (aproveitando `CmdAlterarCampo` via reflection para primitivos, `oneof`, itens de listas e renomeações), adição das ferramentas explícitas para `CmdAlterarImagem` e `CmdAlterarAnexo`, e manutenção das ferramentas de alto nível (`aresta_migrar_setor`, `aresta_adicionar_mapa_arquivo`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown`, `aresta_vincular_referencia_mapa`, etc.) operando sobre os novos comandos canônicos e macros.
- **Isolamento Estrito de Comandos Legados (`editor/commands/comandos_legados.py`) e Guarda AST**:
  - As 12 classes de comando descontinuadas (`CmdAlterarPrimitivo`, `CmdRenomearEscalada`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdAdicionarMapaArquivo`, `CmdSubstituirImagemMemoria`, `CmdMigrarSetor`) são movidas para `editor/commands/comandos_legados.py` (com seu respectivo `comandos_legados_test.py`) para garantir leitura transparente de `diario_pendente.bin` e `diario_salvo.bin` de croquis já em edição.
  - Remoção de código morto de sinais não utilizados em `GerenciadorHistorico` (`CmdRemoverArquivoFisico` e ramificações obsoletas) mantendo apenas o essencial.
  - Adição de teste de arquitetura via AST em `editor/arquitetura_mvc_test.py` garantindo que `comandos_legados.py` e suas classes jamais sejam importados ou instanciados em nenhum arquivo de produção ou teste fora do deserializador de histórico (`deserializar_comando`) e de `comandos_legados_test.py`.

## Capabilities

### New Capabilities
*(Nenhuma nova capacidade de topo introduzida; a consolidação evolui as capacidades existentes de histórico e arquitetura MVC.)*

### Modified Capabilities
- `undo-redo-protobuf`: Substitui a família fragmentada de comandos de edição Protobuf e imagem pelo conjunto canônico de 7 comandos (`CmdAlterarCampo` via reflection, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`, `CmdMacro`), adota endereçamento híbrido ancorado em `UID` com fallback posicional global, compõe operações de alto nível via `CmdMacro` e isola os comandos antigos exclusivamente para deserialização legada.
- `arquitetura-mvc`: Adiciona regra de verificação estática (AST) proibindo a importação ou instanciação de `comandos_legados.py` e de qualquer classe de comando legado fora do ponto único de deserialização do diário (`deserializar_comando`) e do respectivo teste unitário espelhado (`comandos_legados_test.py`).

## Impact

- **Código Afetado**:
  - `editor/commands/comandos_protobuf.py` (e `comandos_protobuf_test.py`)
  - `editor/commands/comandos_legados.py` (e `comandos_legados_test.py`)
  - `editor/commands/comandos_mapas.py` (esvaziado/deprecado em favor de `comandos_legados.py` e composição via `CmdMacro`)
  - `editor/controllers/croqui_controller.py` e `editor/controllers/mapas_controller.py`
  - `editor/models/croqui_model.py` (simplificação de mutadores e suporte a reflection)
  - `editor/core/historico.py` e `editor/core/diario.py`
  - `editor/mcp/ferramentas_comandos.py` e `editor/mcp/resolvedor_alvo.py`
  - `editor/arquitetura_mvc_test.py`
- **Compatibilidade**:
  - Zero alterações no schema `croqui.proto`.
  - 100% de retrocompatibilidade na leitura de arquivos `diario_pendente.bin` e `diario_salvo.bin` gerados por versões anteriores do editor.
