## Por que

Após a seleção de um croqui na tela de carregamento, o usuário precisa de um ambiente de trabalho estruturado para realizar a edição. Atualmente, o editor não possui uma moldura principal que organize as ferramentas globais e permita a alternância entre diferentes visões (edição de metadados, desenho, etc.). Esta mudança estabelece a fundação visual e funcional do aplicativo.

## O que muda

- **Nova Janela Principal**: Implementação da estrutura `JanelaPrincipal` que serve como container para toda a aplicação.
- **Toolbar Superior**: Adição de uma barra de ferramentas no topo com ações globais, em ícones:
    - Abrir novo croqui (volta à tela de carregamento. Confere se precisa salvar o croqui primeiro caso haja modificações)
    - Salvar (grava o croqui na pasta `database`, compila para a pasta `compilado` e faz um commit no repo git local)
    - Desfazer (desfaz a última ação)
    - Refazer (refaz a última ação desfeita)
    - Exportar (gera o `.croqui`)
    - Conectar com Celular (sincronização via rede local)
    - Publicar (cria uma Pull Request no GitHub com as alterações)
- **Toolbar Lateral**: Adição de uma barra lateral esquerda (estilo VS Code) para alternar entre contextos:
    - Dados (editor de metadados principal)
    - Imagens (editor apenas de imagens)
    - Mapas (editor apenas de mapas)
    - Histórico (investigação de histórico git)
- **Área Central Dinâmica**: Um componente central que muda seu conteúdo dependendo da seleção na toolbar lateral. Inicialmente, o conteúdo será a página de 'Dados', que já pode ser criada, mas que será apenas um mock em branco 'a implementar'.
- **Persistência**: Integração com a biblioteca de croqui experimental para carregar e salvar o estado do croqui selecionado.

## Capacidades

### Novas Capacidades
- `editor-area-principal`: Define a estrutura da interface principal, as toolbars superior e lateral, e a lógica de troca de páginas/contextos no editor.

### Capacidades Modificadas
- Nenhuma.

## Impacto

- **UI**: Nova estrutura de janelas baseada em PyQt6.
- **Estado**: Introdução de um gerenciador de estado global para o croqui aberto.
- **Testes**: Necessidade de testes de integração para garantir que a troca de páginas e os botões da toolbar funcionam corretamente.
