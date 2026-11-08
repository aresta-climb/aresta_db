# Proposal

## Why

Após a unificação dos fluxos de entrada e substituição de imagens no `DialogoAdicionarMapa` (e no `DialogoInserirImagemMarkdown`), clicar em `"Substituir Imagem..."`, `"Trocar Imagem..."` ou `"Adicionar Mapa"` passou a demorar vários segundos em croquis reais. Isso ocorre porque `_carregar_imagens_existentes()` é executado sincronamente dentro do `__init__` antes mesmo da janela abrir na Aba 0 (`"Importar Nova Imagem"`), lendo do disco, decodificando em resolução máxima (1 a 2.5 MP) e copiando os bytes brutos de **todas** as imagens do croqui na thread principal da UI, sem cache de miniaturas entre aberturas.

## What Changes

- **Carregamento *Lazy* da Aba `"Imagens do Croqui"` (`DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`)**:
  - Remover a chamada síncrona bloqueante de carregamento da galeria no `__init__` dos diálogos.
  - A abertura da janela na Aba 0 (`"Importar Nova Imagem"`) passa a ser instantânea (`< 5 ms`), sem leitura ou decodificação de imagens existentes no disco.
  - A galeria `"Imagens do Croqui"` passa a ser populada sob demanda quando o usuário alterna para a Aba 1 (ou quando solicitada explicitamente pela interface pública da galeria).
- **Leitura de Bytes Sob Demanda e Miniaturas `96x96` com Cache em Memória**:
  - Os itens da lista da galeria (`QListWidgetItem`) deixam de armazenar cópias completas dos `bytes` brutos de todas as imagens em `UserRole` e `QPixmap` em resolução total.
  - Os `bytes` completos e metadados detalhados (`obter_metadados_imagem`) passam a ser carregados sob demanda exclusivamente para o item que o usuário selecionar na galeria.
  - As miniaturas (`96x96` px) passam a ser redimensionadas e armazenadas em um cache leve em memória (invalidado automaticamente por caminho/mtime no disco ou identidade dos bytes em RAM), tornando reaberturas subsequentes da aba `"Imagens do Croqui"` instantâneas.
- **Renderização Progressiva Não-Bloqueante de Miniaturas na Galeria**:
  - Ao abrir a aba `"Imagens do Croqui"`, os itens e seus nomes são inseridos imediatamente na lista (permitindo busca e seleção instantâneas), enquanto a decodificação de miniaturas ainda não presentes no cache ocorre de forma incremental no loop de eventos sem congelar a interface.

## Capabilities

### New Capabilities
- Nenhuma nova capability de topo; as otimizações refinam os contratos existentes dos diálogos de imagem.

### Modified Capabilities
- `editor-mapas`: Atualiza o requisito `Diálogo Robusto de Adição de Mapas` para exigir abertura instantânea sem leitura/decodificação síncrona da galeria no `__init__`, carregamento *lazy* da aba `"Imagens do Croqui"`, cache de miniaturas `96x96` e leitura sob demanda dos bytes completos apenas na seleção.
- `editor-markdown-imagens`: Atualiza o requisito `Galeria de Imagens do Croqui Atual` para exigir carregamento *lazy* ao acessar a aba `"Imagens do Croqui"` e uso do cache de miniaturas compartilhado sem bloquear a abertura do `DialogoInserirImagemMarkdown`.

## Impact

- **`editor/views/dialogos/dialogo_adicionar_mapa.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown.py`**: Carregamento *lazy* da aba `"Imagens do Croqui"`, leitura sob demanda de bytes na seleção e geração/cache de miniaturas `96x96`.
- **Testes espelhados (`editor/views/dialogos/dialogo_adicionar_mapa_test.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py`)**: Testes comportamentais validando que o `__init__` não carrega a galeria até a troca para a Aba 1, que o cache evita re-decodificação em aberturas repetidas e que alterações em RAM invalidam o cache corretamente.
