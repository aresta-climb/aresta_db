## ADDED Requirements

### Requirement: Mapeamento de Ícones QtAwesome
O sistema SHALL definir um mapeamento centralizado de identificadores de ação para strings de ícones do QtAwesome, garantindo consistência visual em todo o editor.

#### Scenario: Mapeamento da Barra Superior
- **WHEN** os botões da barra superior são renderizados
- **THEN** os seguintes ícones SHALL ser usados:
    - Novo Croqui: `fa5s.folder-open`
    - Salvar: `fa5s.save`
    - Desfazer: `fa5s.undo`
    - Refazer: `fa5s.redo`
    - Exportar: `fa5s.file-export`
    - Celular: `fa5s.mobile-alt`
    - Publicar: `fa5b.github`
    - Logo: `fa5s.mountain`

#### Scenario: Mapeamento da Barra Lateral
- **WHEN** os botões da barra lateral são renderizados
- **THEN** os seguintes ícones SHALL ser usados:
    - Dados: `fa5s.database`
    - Imagens: `fa5s.images`
    - Mapas: `fa5s.map-marked-alt`
    - Histórico: `fa5s.history`

### Requirement: Estilização de Ícones Premium
Os ícones SHALL ter cores e tamanhos consistentes com a estética de luxo do aplicativo.
- **Normal**: `#454545`
- **Destaque**: `#2b579a`
- **Logo**: Verde Musgo `#556b2f` com opacidade 0.7.

### Requirement: Alinhamento Pixel-Perfect
A interface SHALL seguir uma grade rigorosa de alinhamento:
- **Botões Laterais**: Margem de 6px em todos os lados.
- **Barra Lateral**: Largura total de 82px.
- **Barra Superior**: Espaçador inicial de 63px para alinhamento com a barra lateral.
- **Unidades**: Uso de `pt` para fontes para garantir estabilidade visual.
