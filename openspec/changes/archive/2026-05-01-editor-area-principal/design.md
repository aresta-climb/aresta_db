## Contexto

Após o sucesso da implementação da tela de carregamento, o Editor Aresta precisa de um container principal que hospede as ferramentas de edição. Este documento descreve a arquitetura da `JanelaPrincipal` e como ela gerencia o estado do croqui e a navegação entre visões.

## Objetivos / Não-Objetivos

**Objetivos:**
- Implementar a moldura principal do editor usando PyQt6.
- Fornecer navegação lateral persistente para as visões: Dados, Imagens, Mapas e Histórico.
- Implementar uma barra de ferramentas superior com ícones para ações globais (Abrir, Salvar, Desfazer/Refazer, Exportar, Conectar com celular, Publicar).
- Estabelecer um padrão para que páginas injetem botões na barra de ferramentas superior.
- Implementar a lógica de transição reversa para a tela de carregamento (Abrir novo croqui).
- Implementar o fluxo de publicação (Pull Request) via integração com a API do GitHub.

**Não-Objetivos:**
- Implementar a lógica interna de edição de cada página nesta fase (serão mocks).
- Implementar o motor de Undo/Redo completo (apenas o esqueleto/botões na toolbar).

## Decisões

### 1. Estrutura de Layout Base (QMainWindow)
Utilizaremos `QMainWindow` como classe base. O layout será organizado da seguinte forma:
- `QToolBar` superior para ações globais, utilizando apenas ícones para uma estética compacta.
- `QToolBar` lateral esquerda (vertical) para navegação entre contextos.
- `QStackedWidget` como o `centralWidget`, permitindo a troca rápida de páginas.

**Racional:** `QMainWindow` fornece suporte nativo a toolbars e widgets centrais.

### 2. Fluxo de Navegação Global
- **Abrir Novo Croqui**: A `JanelaPrincipal` deve emitir um sinal ou invocar um callback que feche a si mesma e reabra a `TelaDeCarregamento`.
- **Dirty State**: A `JanelaPrincipal` deve monitorar se o croqui foi modificado para exibir um diálogo de aviso ao tentar fechar ou abrir um novo croqui sem salvar.

### 3. Gerenciamento de Estado e Persistência
- **Ação Salvar**: 
    1. Grava os arquivos da mensagem `Croqui` no sistema de arquivos (`database`).
    2. Executa a compilação automática para gerar os artefatos na pasta `compilado`.
    3. Invoca a lógica de commit git local para versionamento.
- **Ação Exportar**: Empacotará o croqui no formato `.croqui`.
- **Ação Conectar com Celular**: Sincronização via rede local.

**Racional:** Integrar a compilação ao salvamento garante que a pasta `compilado` esteja sempre em sincronia com o banco de dados e o histórico git.

### 6. Fluxo de Publicação (Pull Request)
- **Diálogo de Publicação**: Coleta título e descrição da PR.
- **Worker de Publicação**: Executa em segundo plano:
    1. Sincronização do repo base local.
    2. Criação de branch temporária.
    3. Cópia das mudanças da pasta `database` do croqui experimental.
    4. Push para o fork e criação da PR no GitHub.

### 4. Sistema de Páginas (Views)
Cada contexto da barra lateral será uma classe separada herdando de `QWidget`.
- `PaginaDados` (inicialmente com mock)
- `PaginaImagens` (inicialmente com mock)
- `PaginaMapas` (inicialmente com mock)
- `PaginaHistorico` (inicialmente com mock)

### 5. Comunicação Página-Toolbar
A `JanelaPrincipal` oferecerá um método `adicionar_acoes_contextuais(acoes)`. Ao trocar de página, as ações contextuais anteriores são limpas.

## Riscos / Trade-offs

- **[Risco]** Perda de dados ao abrir novo croqui.
  - **Mitigação:** Implementar uma flag `is_dirty` que é verificada antes de qualquer transição de saída da edição.
- **[Trade-off]** Complexidade do Undo/Redo.
  - **Decisão:** Inicialmente, os botões estarão na UI, mas sua funcionalidade dependerá da implementação do padrão Command nas páginas individuais no futuro.
