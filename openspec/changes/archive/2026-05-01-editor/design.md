## Context

O projeto Aresta requer que autores locais possam criar e editar croquis através de uma interface gráfica nativa para desktop (Editor Aresta). Atualmente, as opções são limitadas ou inexistentes de forma escalável e sem dor para não-desenvolvedores. O projeto `editor` atuará como um cliente PyQt6 autônomo. O objetivo atual é estruturar a fundação do editor (empacotamento, inicialização e página inicial com navegação), que permitirá aos usuários gerenciar croquis experimentais na sua máquina, antes de mergulharmos nas telas de edição profunda.

## Goals / Non-Goals

**Goals:**
- Estruturar um projeto Python limpo, utilizando PyQt6 como biblioteca de UI.
- Estabelecer scripts para build usando PyInstaller que gerem um executável sem dependências instaláveis extras.
- Implementar a rotina de inicialização, criando a pasta no armazenamento local do usuário e baixando os dados de base do último commit de `aresta_db` usando o Git localmente.
- Implementar a UI da página inicial que apresente um dashboard de arquivos de croqui experimentais recentes e três ações principais (Novo croqui, Importar croqui experimental e Editar croqui oficial).

**Non-Goals:**
- Não iremos implementar o fluxo de salvamento e compilação do arquivo `.croqui` (ZIP com Protobuf e Imagens) neste momento, apenas criar a estrutura de pastas e ler os diretórios como forma de "abrirmos" na lista.
- Não iremos implementar as telas do Editor Protobuf neste momento (árvore esquerda e sub-páginas form). O clique em um croqui experimental ou a criação de um novo vai apenas levar para um placeholder da área principal vazia (ou imprimir um log), a ser implementada na próxima fase.
- Não implementaremos integração via OAuth nem criação de Pull Request no Github agora.

## Decisions

- **GUI com PyQt6:** Escolhido por ser robusto, oferecer componentes nativos de UI cross-platform e ter vasta documentação, essencial para o desenvolvimento Desktop em Python.
- **Estrutura de Pastas de Dados Locais:** Utilizar os caminhos padrão do SO para dados de aplicação (ex: `QStandardPaths.StandardLocation.AppDataLocation`) para guardar a pasta com o clone base do último commit do repositório `aresta_db` e a pasta `croquis_experimentais`.
- **Uso do GitPython:** Para a inicialização, precisaremos baixar a base oficial de croquis. Em vez de usar requisições HTTP isoladas, faremos clone raso do branch principal e usaremos Git para facilitar as atualizações futuras (quando formos fazer o sync).
- **Gerenciador de Layout (Main Window):** O `QMainWindow` terá um layout de QSplitter onde a lateral esquerda ficará responsável pelos menus de "Página inicial", "Editor", etc (Toolbar clássico), e o painel direito terá um QStackedWidget que permuta entre a Página Inicial (nesta fase) e as futuras abas do editor propriamente dito.

## Risks / Trade-offs

- **[Risco] Tamanho do Executável PyInstaller:** O binário gerado pode ficar pesado com Qt6 e GitPython embutidos. → **Mitigação**: O tamanho final é irrelevante frente à facilidade do usuário final apenas fazer "double-click".
- **[Risco] Lentidão no clone inicial via GitPython:** Dependendo do tamanho do repositório `aresta_db`, a abertura do programa na primeira vez pode demorar. → **Mitigação**: Criar um splash screen ou barra de progresso para UX amigável durante esta inicialização; considerar um *shallow clone* (`--depth=1`).
- **[Risco] Sujeira no AppData:** Falha ao criar novos croquis ou arquivos corrompidos podem acumular. → **Mitigação**: Isolamento estrito na pasta `croquis_experimentais` por timestamp como já especificado, facilitando limpeza se necessário.
