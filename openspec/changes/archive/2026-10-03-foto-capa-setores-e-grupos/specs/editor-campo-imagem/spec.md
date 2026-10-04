# Spec Delta: editor-campo-imagem

## ADDED Requirements

### Requirement: Orçamento de Imagem de 1 Megapixel para Capas
O sistema SHALL suportar a aplicação do limite de resolução de 1.000.000 pixels (`AREA_MAXIMA_ESCALADA` / 1 MP) na compressão WebP em memória ao inserir ou trocar fotos através do campo de capa (`caminho_imagem_capa`).

#### Scenario: Inserção de foto de capa de alta resolução
- **WHEN** o usuário seleciona uma imagem de 12 megapixels (ex: 4000x3000 px) no campo de foto de capa de um Setor ou Grupo
- **THEN** o sistema redimensiona a imagem para que a área total não exceda 1.000.000 pixels, preservando a proporção original e comprimindo em WebP Q85 na memória RAM

### Requirement: Exibição Priorizada de Capa no Topo do Formulário
O sistema SHALL renderizar o campo `caminho_imagem_capa` no topo absoluto do formulário de dados de entidades `Setor` e `Grupo`, posicionado antes do campo `nome`.

#### Scenario: Renderização de formulário de Setor com capa
- **WHEN** o formulário de visualização/edição de um `Setor` é exibido na interface do usuário
- **THEN** o widget de imagem associado ao campo `caminho_imagem_capa` é posicionado como primeiro elemento da área principal do formulário, acima do campo de texto `nome`

#### Scenario: Renderização de formulário de Grupo com capa
- **WHEN** o formulário de visualização/edição de um `Grupo` é exibido na interface do usuário
- **THEN** o widget de imagem associado ao campo `caminho_imagem_capa` é posicionado como primeiro elemento da área principal do formulário, acima do campo de texto `nome`
