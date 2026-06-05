## 1. Infraestrutura e Testes Iniciais

- [x] 1.1 Criar o arquivo de teste de integração `editor/views/area_principal_test.py`
- [x] 1.2 Criar a classe `JanelaPrincipal` em `editor/views/area_principal.py` herdando de `QMainWindow`
- [x] 1.3 Criar as classes de mock para as páginas: `PaginaDados`, `PaginaImagens`, `PaginaMapas` e `PaginaHistorico`
- [x] 1.4 Implementar teste que verifica se a janela abre exibindo inicialmente a `PaginaDados`

## 2. Implementação do Layout e Toolbars

- [x] 2.1 Implementar a `TopToolbar` com ícones para: Abrir Novo, Salvar, Desfazer, Refazer, Exportar, Celular e Publicar
- [x] 2.2 Implementar a `SideToolbar` (vertical) com ícones para as 4 visões (Dados, Imagens, Mapas, Histórico)
- [x] 2.3 Configurar o `QStackedWidget` como widget central e adicionar as 4 páginas a ele

## 3. Lógica de Navegação e Persistência

- [x] 3.1 Implementar a troca de páginas no `QStackedWidget` ao clicar nos ícones da `SideToolbar`
- [x] 3.2 Integrar a `JanelaPrincipal` com `CroquiExperimental` para carregar o croqui selecionado
- [x] 3.3 Implementar ação do botão "Abrir Novo": fechar janela principal e reabrir carregamento (com aviso de salvamento)
- [x] 3.4 Implementar ação do botão "Salvar": salvar em `database/`, compilar para `compilado/` e realizar commit git local
- [x] 3.5 Implementar esqueletos das ações de Desfazer/Refazer na toolbar
- [x] 3.6 Implementar ação do botão "Exportar": gerar arquivo `.croqui` (ZIP)

## 4. Dinamismo e Fluxo do Aplicativo

- [x] 4.1 Implementar sistema de ações contextuais na `TopToolbar` (adicionar/remover botões via página ativa)
- [x] 4.2 Garantir limpeza automática de botões contextuais ao trocar de visão na barra lateral
- [x] 4.3 Atualizar o fluxo de navegação entre `TelaDeCarregamento` e `JanelaPrincipal` para suportar ida e volta
- [x] 4.4 Implementar funcionalidade "Publicar" (Pull Request no GitHub) com worker em segundo plano e diálogos de feedback
