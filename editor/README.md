# Aresta Editor

O módulo `editor` implementa a interface gráfica principal do Aresta Editor.
Para garantir estabilidade, testabilidade e separação de responsabilidades (evitando loops infinitos e bugs de estado na UI), adotamos uma arquitetura MVC (Model-View-Controller) rigorosa orientada a comandos de histórico.

## Estrutura de Diretórios
- **`models/`**: O estado real da aplicação. Encapsula o Protobuf e expõe sinais e métodos públicos apenas para leitura. Métodos que mutam o Model são protegidos (`_set_*`) e exclusivos da camada `commands/`.
- **`views/`**: Componentes da interface visual. São "Views burras". Não mutam o Model. Apenas leem do Model para se renderizar e disparam intenções para os Controllers ao sofrer interação do usuário.
- **`controllers/`**: Orquestradores. Recebem intenções das Views, instanciam `QUndoCommand`s e os enviam para o Gerenciador de Histórico.
- **`commands/`**: Único lugar permitido a alterar o estado do Model e do Protobuf através dos métodos `_set_*`. Garantem que cada mudança é rastreável e passível de Undo/Redo.
- **`legacy_views/`**: Componentes de interface que ainda não foram migrados para o padrão MVC. Não devem ser tomados como exemplo para novos desenvolvimentos.

## Arquitetura de Fluxo de Dados (MVC)

O diagrama abaixo ilustra como os componentes do editor interagem em um fluxo de dados unidirecional:

```mermaid
flowchart TD
    %% Componentes
    View["Views\n(Interface UI)"]
    Controller["Controllers\n(Lógica de Ação)"]
    UndoStack{"QUndoStack\n(Gerenciador de Histórico)"}
    Command["Commands\n(Comandos)"]
    Model["Models\n(Estado Seguro)"]
    Protobuf[("Protobuf\n(Dados Brutos)")]

    %% Fluxo
    View -- "1. Intenção do Usuário\n(ex: editar texto)" --> Controller
    Controller -- "2. Instancia e Empilha" --> UndoStack
    UndoStack -- "3. Executa / Desfaz" --> Command
    Command -- "4. Mutação de Estado\n(chama métodos privados _set_*)" --> Model
    Model -- "5. Lê / Modifica" --> Protobuf
    Model -- "6. Emite Sinais QT\n(ex: dataChanged)" --> View
    View -- "7. Lê Estado Atualizado" --> Model

    %% Estilos
    classDef view fill:#d4e157,stroke:#333,stroke-width:2px,color:#000;
    classDef controller fill:#4fc3f7,stroke:#333,stroke-width:2px,color:#000;
    classDef model fill:#ffb74d,stroke:#333,stroke-width:2px,color:#000;
    classDef command fill:#ce93d8,stroke:#333,stroke-width:2px,color:#000;
    
    class View view;
    class Controller controller;
    class Model,Protobuf model;
    class Command,UndoStack command;
```
