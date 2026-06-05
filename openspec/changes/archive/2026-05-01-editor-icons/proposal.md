## Why

O editor atualmente utiliza ícones padrão do sistema ou placeholders que não proporcionam uma experiência visual premium e moderna. A integração da biblioteca `QtAwesome` permitirá o uso programático de coleções de ícones amplamente reconhecidas (como Font Awesome e Material Design Icons), facilitando a criação de uma interface consistente, elegante e de fácil manutenção.

## What Changes

- **Requirement**: Adicionar `qtawesome` às dependências do projeto no arquivo `editor/requirements.txt`.
- **UI Update**: Substituir todos os ícones da Janela Principal por ícones premium via `QtAwesome` e implementar o logo de montanha "Verde Musgo".
- **Styling**: Configurar cores e tamanhos padrão, garantindo alinhamento pixel-perfect (margens de 6px) e simetria visual.
- **Robustness**: Eliminar avisos de renderização de fonte do Qt (`QFont::setPointSize`) e implementar testes de regressão para garantir terminal limpo.
- **Utility**: Centralizar mapeamento em `editor/views/estilo.py`.

## Capabilities

### New Capabilities
- `editor-visual-icons`: Especificação do mapeamento de ações da interface para ícones específicos do QtAwesome e suas respectivas propriedades visuais (cor, tamanho, animação).

### Modified Capabilities
- `editor-area-principal`: Atualização dos requisitos visuais da moldura principal para incluir a obrigatoriedade do uso de ícones premium via QtAwesome.

## Impact

- **Dependências**: Adição de `qtawesome`.
- **Código**: Alterações em `editor/views/janela_principal.py` (ou equivalente) para carregar os novos ícones.
- **Distribuição**: O script de build e empacotamento deve garantir a inclusão das fontes de ícones do QtAwesome.
