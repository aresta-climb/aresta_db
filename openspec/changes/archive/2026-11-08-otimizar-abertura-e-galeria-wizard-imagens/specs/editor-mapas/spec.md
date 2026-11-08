## MODIFIED Requirements

### Requirement: Diálogo Robusto de Adição de Mapas
O sistema SHALL fornecer um diálogo unificado para adição e substituição de mapas contendo duas abas (`"Importar Nova Imagem"` com seleção de arquivo, Drag & Drop, barra de recorte interativo *rubber-band crop*, painel de metadados ricos e pré-processamento WebP em RAM; e `"Imagens do Croqui"` com busca textual e grade de miniaturas do disco e da memória RAM carregada sob demanda), validação de nomes e opção de reajuste proporcional de POIs no modo de substituição, abrindo instantaneamente sem decodificar a galeria durante a inicialização.

#### Scenario: Abertura Instantânea na Aba de Importação sem Bloqueio da Galeria
- **WHEN** o diálogo unificado de mapas e imagens é instanciado na aba inicial `"Importar Nova Imagem"`
- **THEN** o sistema SHALL abrir a janela imediatamente sem ler nem decodificar os arquivos da pasta `imagens/` no construtor, postergando o carregamento da galeria até que o usuário alterne para a aba `"Imagens do Croqui"`

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem na aba `"Importar Nova Imagem"` do diálogo de mapa
- **THEN** o sistema SHALL exibir a pré-visualização gráfica com suporte a seleção de área de recorte (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), apresentar resolução ($W \times H$), tamanho e formato nos metadados e pré-processar os bytes para WebP

#### Scenario: Seleção de Imagem na Galeria do Croqui
- **WHEN** o usuário alterna para a aba `"Imagens do Croqui"`, filtra ou seleciona uma miniatura existente na pasta `imagens/` ou em `_imagens_em_memoria`
- **THEN** o sistema SHALL exibir miniaturas `96x96` reutilizando cache em memória (invalidado automaticamente por alteração em disco ou RAM), carregar os bytes completos e metadados apenas do item selecionado e habilitar a confirmação sem exigir reimportação de arquivo externo

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o diálogo opera em modo de adição e o usuário digita um nome de arquivo que já existe no buffer de memória RAM (`_imagens_em_memoria`) ou na pasta `imagens/` do disco
- **THEN** o sistema SHALL exibir alerta indicando o conflito e desabilitar a confirmação
- **WHEN** o diálogo opera em modo de substituição com destino fixo (`caminho_destino_fixo`)
- **THEN** o sistema SHALL permitir a substituição sobre o caminho alvo sem bloquear por colisão consigo mesmo
