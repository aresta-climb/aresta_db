## ADDED Requirements

### Requirement: Painel de Edição de Referências
The system SHALL fornecer um painel à direita no Editor de Mapas para visualização, criação e edição de referências do mapa selecionado.

#### Scenario: Visualização de referências existentes
- **WHEN** o mapa atual possuir referências configuradas no CroquiModel
- **THEN** o painel direito SHALL listar todas as referências com seus respectivos alvos lógicos

### Requirement: Criação de Nova Referência via Busca
The system SHALL permitir a adição de novas referências buscando entidades lógicas (Grupos, Setores, Escaladas) no CroquiModel.

#### Scenario: Busca por entidade
- **WHEN** o usuário clica em "Nova Referência"
- **THEN** um modal de busca abrangendo todo o croqui é exibido para seleção do alvo

### Requirement: Linkagem Interativa de Formas
The system SHALL fornecer um modo especial de interação de mouse ("Linkagem") para associar formas desenhadas (círculos/retângulos) à Referência ativa.

#### Scenario: Adicionando IDs à referência
- **WHEN** no modo de Linkagem, o usuário clica sobre uma forma do mapa
- **THEN** o ID da forma é adicionado à lista de IDs da Referência no painel

### Requirement: Ajuste Visual de Câmera (WYSIWYG)
The system SHALL permitir que o usuário defina o `ajuste_de_camera` manipulando uma caixa de proporção vertical (ex: 9:16) diretamente sobre a imagem do mapa.

#### Scenario: Simulação do app móvel com margens de corte
- **WHEN** o usuário ativa o ajuste de câmera para uma referência
- **THEN** o sistema exibe um overlay translúcido com a exata proporção da tela do celular, escurecendo adicionalmente os 20% superiores e os 20% inferiores (indicando as áreas que serão parcialmente obstruídas por UI do aplicativo móvel)
