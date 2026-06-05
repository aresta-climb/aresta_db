## 1. Setup Arquitetural

- [x] 1.1. Criar pastas vazias com `__init__.py` e `README.md`: `editor/models`, `editor/views`, `editor/controllers`, `editor/commands`, `editor/legacy_views`.
- [x] 1.2 Mover os arquivos de interface de Mapas e Imagens para `legacy_views/` e reajustar os imports em todo o sistema.
- [x] 1.3 Mover `editor/core/comandos_protobuf.py` para `editor/commands/`.
- [x] 1.4 Criar os arquivos `README.md` em `editor/` e dentro de cada nova sub-pasta para documentar as regras da arquitetura MVC orientada a comandos.
- [x] 1.5 Executar a aplicação e as suítes de testes existentes para garantir que o sistema (incluindo as views legadas) está funcionando perfeitamente antes da refatoração da aba de Dados.
- [x] 1.6 Realizar o commit das alterações de Setup Arquitetural.

## 2. Teste Arquitetural Estático (AST)

- [x] 2.1 Criar `editor/arquitetura_mvc_test.py` (TDD): o teste deve escanear todos os arquivos do aplicativo e garantir que métodos `_set_*` da pasta `models/` sejam chamados apenas de dentro de `models/` e `commands/`. Para seguir o TDD, introduza propositalmente uma chamada `_set_` inválida no código, rode o teste e certifique-se de que ele falha (Red), depois remova a infração para ver o teste passar (Green).
- [x] 2.2 Implementar a lógica robusta de parsing (Abstract Syntax Tree) no próprio `editor/arquitetura_mvc_test.py` garantindo sua robustez.
- [x] 2.3 Realizar o commit das alterações do Teste Arquitetural.

## 3. Implementação do Model (TDD)

- [x] 3.1 Criar `editor/models/croqui_model_test.py` (TDD) projetando o comportamento esperado: encapsulamento do Protobuf, emissão de sinais, métodos públicos de leitura e métodos `_set_*` (protegidos) de escrita.
- [x] 3.2 Criar `editor/models/croqui_model.py` implementando a classe base de Modelo e fazendo os testes passarem.
- [x] 3.3 Realizar o commit das alterações do Model.

## 4. Implementação do Controller (TDD)

- [x] 4.1 Criar `editor/controllers/croqui_controller_test.py` (TDD) definindo a lógica de orquestração: ao receber intenções da View, o Controller deve despachar `QUndoCommand`s instanciados.
- [x] 4.2 Criar `editor/controllers/croqui_controller.py` com a implementação do Controller fazendo os testes passarem.
- [x] 4.3 Adaptar os comandos movidos para `editor/commands/` para operarem com os métodos `_set_*` do Model, e atualizar seus testes (`editor/commands/comandos_protobuf_test.py` ou equivalentes) para refletirem essas mudanças na API do Model.
- [x] 4.4 Realizar o commit das alterações do Controller e dos Comandos.

## 5. Refatoração da View e Integração

- [x] 5.1 Criar (ou adaptar) `editor/views/widget_editor_dados_test.py` para validar que a View ouve sinais do Model corretamente e despacha intenções ao Controller, sem tocar nos métodos `_set_*`.
- [x] 5.2 Refatorar completamente o `WidgetEditorDados` (movendo-o definitivamente para `editor/views/`), limpando toda a lógica de estado e geração de comandos, tornando-o uma view passiva, e fazer seus testes passarem.
- [x] 5.3 Ajustar a instanciação no `area_principal.py` para criar o `CroquiModel`, `CroquiController` e conectá-los ao `WidgetEditorDados` e ao `GerenciadorHistorico`.
- [x] 5.4 Realizar o commit das alterações da View e da Integração.

## 6. Validação Final

- [x] 6.1 Rodar a suíte completa de testes (unitários e arquiteturais) garantindo que nenhum teste falhou.
- [x] 6.2 Executar o aplicativo, abrir um projeto, editar dados da árvore Protobuf e validar que as funcionalidades e o Undo/Redo operam perfeitamente através das novas camadas.
- [x] 6.3 Realizar o commit final atestando o sucesso da migração.
