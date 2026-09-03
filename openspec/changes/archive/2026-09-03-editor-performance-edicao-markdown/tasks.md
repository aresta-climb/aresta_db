## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 1.1 (TDD - Vermelho) Criar casos de teste de integração em `editor/views/campos_customizados_integracao_test.py` simulando digitação contínua e rápida em campo Markdown, verificando a preservação da responsividade, a consolidação retardada no modelo via `QUndoCommand`, a capacidade de desfazer/refazer (`Ctrl+Z` / `Ctrl+Y`) e a ausência de chamadas redundantes de renderização ou reconstrução de mapas.

## 2. Biblioteca Autônoma de Coalescência de Digitação (Princípio II - Library-First & Princípio IV - TDD)

- [x] 2.1 (TDD - Vermelho) Criar a suíte de testes unitários `editor/core/temporizador_coalescencia_test.py` definindo os contratos para a classe `TemporizadorCoalescencia` (`agendar`, `descartar`, `forcar_descarga`, `esta_ativo`).
- [x] 2.2 (TDD - Verde) Implementar a biblioteca pura e autossuficiente `editor/core/temporizador_coalescencia.py` utilizando `QTimer` para temporização adiada e execução imediata de funções de retorno (*callbacks*).
- [x] 2.3 (TDD - Refatorar) Assegurar conformidade de tipagem estática e 100% de cobertura de testes unitários na biblioteca (Princípio III).

## 3. Integração no Editor Markdown com Prevenção de Duplo Render (Princípio VII & Princípio IV - TDD)

- [x] 3.1 (TDD - Vermelho) Criar testes unitários em `editor/views/widget_editor_dados_test.py` verificando a coalescência de digitação no `WidgetEditorMarkdown`, a execução imediata em caso de perda de foco (`focusOutEvent`), e a guarda em `set_conteudo` para evitar re-renderização e re-escaneamento de imagens quando o texto recebido for idêntico ao já contido no editor.
- [x] 3.2 (TDD - Verde) Integrar `TemporizadorCoalescencia` em `WidgetEditorMarkdown`, implementar o salvamento forçado no `focusOutEvent` e adicionar a guarda de igualdade em `set_conteudo`.
- [x] 3.3 (TDD - Refatorar) Garantir tipagem estática e aprovação de todos os testes unitários da visualização de dados.

## 4. Instalação Idempotente de Filtros de Evento (Princípio VI - Simplicidade & Princípio IV - TDD)

- [x] 4.1 (TDD - Vermelho) Criar teste unitário em `editor/views/widget_editor_dados_test.py` demonstrando que invocações sucessivas de `_on_campo_alterado` não instalam instâncias duplicadas de `GlobalUndoRedoFilter` no mesmo widget.
- [x] 4.2 (TDD - Verde) Implementar guarda idempotente (`_undo_filter_instalado`) em `WidgetFormularioPadrao._on_campo_alterado` para evitar acúmulo de filtros na cadeia de eventos do Qt.
- [x] 4.3 (TDD - Refatorar) Garantir código limpo e conformidade total de cobertura no módulo de formulários.

## 5. Sincronização Incremental no Diário de Comandos (Princípio VII & Princípio IV - TDD)

- [x] 5.1 (TDD - Vermelho) Criar testes em `editor/core/historico_test.py` e `editor/core/diario_test.py` verificando que a mesclagem de comandos na pilha de Undo (`mergeWith`) não descarta `_comandos_anonimizados_cache` e não relê arquivos de diário em disco desnecessariamente.
- [x] 5.2 (TDD - Verde) Implementar método no `GerenciadorDiario` e ajustar `GerenciadorHistorico` para atualizar comandos mesclados preservando o cache em memória e evitando truncamento destrutivo e releituras de disco a cada caractere.
- [x] 5.3 (TDD - Refatorar) Garantir que todos os testes de persistência, diário e telemetria passem com 100% de cobertura.

## 6. Filtragem Estrita de Sinais no Editor de Mapas (Princípio VI & Princípio IV - TDD)

- [x] 6.1 (TDD - Vermelho) Criar testes em `editor/views/widget_editor_mapas_test.py` garantindo que alterações emitidas para campos textuais (`conteudo`, `descricao`, `notas`) não acionem a reconstrução da lista lateral de mapas em `_atualizar_lista_mapas`.
- [x] 6.2 (TDD - Verde) Modificar a guarda de `_atualizar_lista_mapas` para ignorar sumariamente eventos de alteração em campos textuais que não afetem a estrutura dos mapas.
- [x] 6.3 (TDD - Refatorar) Garantir conformidade com os testes existentes do editor de mapas.

## 7. Verificação Global de Cobertura e Integridade (Princípio III & Princípio I)

- [x] 7.1 Executar a suíte completa de testes com medição de cobertura (`pytest --cov`) assegurando 100% de cobertura de código nos módulos novos e modificados.
- [x] 7.2 Validar conformidade de tipagem e linters (`mypy` e `ruff`) e garantir que todo o código, docstrings e comentários estejam estritamente em português brasileiro.
