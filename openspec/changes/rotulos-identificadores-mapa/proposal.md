## Why

Ao traçar caminhos vetoriais com múltiplos segmentos no editor de mapas, o aplicativo móvel (`aresta_app`) passou a exibir identificadores técnicos internos (ex: `linha_12-linha_16-linha_9-linha_18-linha_21`) nos badges de vias em vez do codenome real da via (ex: `5-C`). Isso ocorreu devido a um fallback indevido para o ID do ponto de interesse quando o campo `label` está vazio, ignorando os rótulos contidos nos nós de linha (`CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `FIM_TOP`).

Além disso, o editor de mapas (`aresta_db`) não fornece aos autores feedback visual em tempo real do codenome resultante de uma referência e nem permite inverter ou ajustar a ordem dos traços linkados caso a sequência tenha sido clicada de forma invertida. Por fim, a remoção do fallback de ID no aplicativo pode silenciar vias em croquis legados onde o autor esqueceu de preencher o label; para evitar isso, o pipeline de compilação/deploy deve emitir um aviso explícito quando uma referência não possuir nenhum identificador.

## What Changes

- **aresta_app**:
  - Implementação de um módulo utilitário centralizado (`extrairRotuloReferencia`) para extrair rótulos e círculos identificadores na ordem sequencial dos IDs e dos nós.
  - Eliminação completa do fallback para IDs de POIs (`labels.add(id)`), garantindo que IDs técnicos de banco de dados (`linha_XX`) nunca sejam exibidos ao usuário.
  - Atualização de `mapa_interativo.dart` e `setor_functions.dart` para consumir o novo utilitário.
  - Ocultação elegante da pílula/badge quando a referência não possuir nenhum rótulo/círculo.
- **aresta_db**:
  - Inclusão de aviso no validador de referências durante `deploy_generated.py` / `validar_referencias_mapa`:
    *"A referência '{nome}' no Mapa {idx} em {contexto} não possui label ou rótulo em círculo identificador e não exibirá identificador no mapa do aplicativo."*
  - Melhorias no `CardReferencia` do editor: exibição de preview do codenome (ex: `[ 5-C ]` ou `[ ⚠️ Sem rótulo ]`) e botão para inverter a ordem dos IDs da referência (`[ 🔄 Inverter ]`), com histórico Undo/Redo.

## Capabilities

### New Capabilities
- `resolucao-rotulos-referencia`: Especifica a extração padronizada de rótulos/codenomes de referências no aplicativo móvel a partir de círculos identificadores e labels de POIs na ordem natural, além da regra de validação no deploy de croquis alertando sobre referências sem identificadores.

### Modified Capabilities
- `editor-mapas-referencias`: Adiciona os requisitos de preview visual do codenome no card da referência e de controle da ordem dos IDs linkados (inversão e reordenação) com suporte completo a Undo/Redo.

## Impact

- **Código Afetado**:
  - `aresta_app/frontend/lib/utils/resolvedor_rotulos_referencia.dart` (novo)
  - `aresta_app/frontend/lib/pages/mapa_interativo.dart`
  - `aresta_app/frontend/lib/view_functions/setor_functions.dart`
  - `aresta_db/scripts/preparar_submissao_lib.py` (`validar_referencias_mapa`)
  - `aresta_db/scripts/deploy_generated.py`
  - `aresta_db/editor/views/widget_painel_referencias.py`
  - `aresta_db/editor/controllers/mapas_controller.py`
- **Compatibilidade**: Totalmente retrocompatível com o modelo Protobuf existente; não requer migrações de schema.
