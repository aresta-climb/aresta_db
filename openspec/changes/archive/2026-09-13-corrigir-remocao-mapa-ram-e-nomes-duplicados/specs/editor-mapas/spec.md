## MODIFIED Requirements

### Requirement: Diálogo Robusto de Adição de Mapas
O sistema DEVE fornecer um diálogo robusto para adição de novos mapas contendo botão explícito de seleção de arquivos, suporte a arrastar e soltar (drag & drop), painel de metadados ricos (dimensões, tamanho formatado e formato), pré-processamento WebP automático em RAM e validação de nomes e colisões em tempo real.

#### Scenario: Seleção de Arquivo com Exibição de Metadados e Pré-processamento
- **WHEN** o usuário seleciona ou arrasta um arquivo de imagem no diálogo de adição de mapa
- **THEN** o sistema DEVE exibir a pré-visualização gráfica, apresentar resolução ($W \times H$), tamanho e formato original nos metadados, e pré-processar os bytes para WebP.

#### Scenario: Validação de Conflito de Nomes em Tempo Real
- **WHEN** o usuário digita um nome de arquivo que já existe no buffer de memória RAM (`_imagens_em_memoria`)
- **THEN** o sistema DEVE exibir alerta indicando conflito na memória RAM e desabilitar a confirmação
- **WHEN** o usuário digita um nome de arquivo que não existe na RAM mas já existe na pasta `imagens/` do disco
- **THEN** o sistema DEVE exibir alerta indicando conflito no disco e desabilitar a confirmação
- **WHEN** um mapa foi removido e sua imagem não está mais na memória RAM nem no disco
- **THEN** o sistema DEVE considerar o nome válido e liberar a confirmação
