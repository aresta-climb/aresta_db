## Context

Atualmente, o editor de dados exibe botões `[Adicionar]` e `[Remover]` no cabeçalho de cada card de campo para refletir explicitamente a presença de campos no Protobuf (`has_presence`). Isso causa poluição visual significativa, obriga o usuário a clicar em `[Adicionar]` antes de editar qualquer propriedade e exibe botões vermelhos de `[Remover]` em campos preenchidos.

A proposta é tornar todos os campos diretamente editáveis por padrão e inferir a presença ou ausência automaticamente conforme o conteúdo: campos vazios são automaticamente removidos (`ClearField`), e campos com dados são marcados como presentes.

## Goals / Non-Goals

**Goals:**
- Eliminar completamente os botões individuais de `[Adicionar]` e `[Remover]` de campos primitivos e submensagens inline nos formulários.
- Implementar a regra "Vazio = Ausente": esvaziar um campo de texto ou markdown remove a presença do campo no Protobuf e no YAML; preencher restaura a presença.
- Representar campos booleanos como `QComboBox` tri-state (`Não informado`, `Sim`, `Não`), permitindo textos semânticos customizados via extensões do Protobuf (`booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`).
- Diferenciar inteiros de floats:
  - Floats e Coordenadas GPS utilizam `QLineEdit` com validação numérica, garantindo precisão e preservando ausência quando vazios.
  - Inteiros utilizam `QSpinBox` com suporte a estado nulo/vazio ("Não definido"), diferenciando ausência de `0`.
- Submensagens inline (ex: `Coordenada`) exibem seus campos filhos diretamente; se todos os filhos estiverem vazios, a submensagem pai é limpa via `ClearField`.
- Garantir que toda alteração de presença e valor seja executada estritamente via comandos de histórico (`QUndoCommand`), com 100% de reversibilidade (Undo/Redo).
- Cumprir 100% das diretrizes do `PRINCIPIOS.md` (Tudo em Português, Library-First, 100% Unit Test Coverage, TDD, Testes de Integração em Primeiro Lugar, Simplicidade e Histórico).

**Non-Goals:**
- Alterar o comportamento de listas (`repeated`), que continuarão utilizando botões de adicionar e remover itens devido à sua cardinalidade dinâmica.
- Modificar o formato binário do Protobuf ou a lógica de compilação do banco de dados.

## Aderência aos Princípios de Engenharia (PRINCIPIOS.md)

1. **I. Tudo em Português**:
   - Todas as variáveis, nomes de funções, comentários, testes e mensagens na interface são em português brasileiro.
   - Nomes de extensões no Protobuf: `booleano_texto_indefinido`, `booleano_texto_sim`, `booleano_texto_nao`.

2. **II. Library-First**:
   - Os componentes de UI especializados (como seleção tri-state, spinboxes com suporte a nulo e campos de float) são construídos de forma modular na camada de visualização (`editor/views/protobuf_widget_factory.py`), com responsabilidades bem delimitadas e testabilidade autônoma.

3. **III. 100% de unit test coverage & IV. Imperativo do Teste em Primeiro Lugar (TDD)**:
   - Todo arquivo modificado ou criado (`.py`) possui seu respectivo arquivo de teste (`_test.py`) no mesmo diretório.
   - Nenhuma linha de código de produção é escrita antes da criação de testes unitários que falhem primeiro (Red-Green-Refactor).
   - O projeto deve manter 100% de cobertura de testes unitários em todos os módulos afetados.

4. **V. Testes de Integração em Primeiro Lugar**:
   - Antes de iniciar a implementação detalhada dos componentes, são criados testes de integração em `widget_editor_dados_historico_test.py` e `widget_editor_dados_test.py` verificando o ciclo de ponta a ponta: renderização do formulário $\rightarrow$ alteração de campos para vazio $\rightarrow$ emissão de comandos $\rightarrow$ serialização YAML $\rightarrow$ Desfazer (Undo) e Refazer (Redo).

5. **VI. Simplicidade e Anti-Abstração**:
   - A remoção de botões e o mapeamento de "Vazio = Ausente" tornam a arquitetura mais direta e simples, eliminando estados intermediários e listeners complexos de alternância de botões nos layouts.

6. **VII. Edições de Estado via Comandos do Histórico (Undo/Redo)**:
   - Nenhuma mutação direta no objeto Protobuf é realizada nos callbacks da interface gráfica.
   - Toda alteração de valor (seja definir um novo valor ou esvaziar/chamar `ClearField`) dispara o método correspondente no `CroquiController`, que empilha uma instância de `QUndoCommand` na pilha global `historico`.
   - O comando armazena se o campo estava presente anteriormente e o valor antigo, permitindo desfazer perfeitamente a remoção/adição do campo.

## Decisions

### Decisão 1: Booleanos como QComboBox Tri-State com Opções Protobuf
- **Escolha**: Usar `QComboBox` com 3 itens: índice 0 = `Não informado` (valor `None` / `ClearField`), índice 1 = `Sim` (`True`), índice 2 = `Não` (`False`).
- **Alternativa considerada**: `QCheckBox` com `Qt.PartiallyChecked`. Rejeitada porque o estado parcialmente checado de um checkbox não é visualmente autoexplicativo para usuários leigos em relação a "Não informado" vs "Não".
- **Extensões no Protobuf**: Adicionar em `croqui.proto` as opções de campo `booleano_texto_indefinido`, `booleano_texto_sim` e `booleano_texto_nao` para que cada booleano possa expressar sua semântica natural (ex: "Possui sinal" vs "Sem sinal").

### Decisão 2: QLineEdit para Floats e Coordenadas em vez de QDoubleSpinBox
- **Escolha**: Utilizar `QLineEdit` com `QDoubleValidator` / regex para pontos flutuantes e coordenadas.
- **Alternativa considerada**: `QDoubleSpinBox`. Rejeitada porque impõe número fixo de casas decimais, trunca coordenadas de alta precisão do GPS e dificulta a cópia/colagem de valores.
- **Vazio**: Quando a string for `""`, o campo float/coordenada é considerado ausente.

### Decisão 3: QSpinBox Nullable para Inteiros
- **Escolha**: `QSpinBox` configurado com valor mínimo especial ou placeholder representando "Não definido".
- **Comportamento**: Quando no estado "Não definido", o campo é tratado como ausente (`ClearField`). Se o usuário definir `0`, `1`, etc., o valor numérico é gravado explicitamente no Protobuf e YAML, permitindo diferenciar a presença de `0` da ausência de valor.

### Decisão 4: Esvaziamento e Presença Transparente em Submensagens Inline
- **Escolha**: Para mensagens filhas renderizadas inline (como `localizacao_estacionamento: Coordenada`), os campos filhos são sempre renderizados. Ao alterar qualquer filho, a submensagem pai é criada se ainda não existir. Se todos os campos filhos forem apagados (strings vazias), o editor executa `ClearField` da submensagem pai no objeto principal.

### Decisão 5: Integração com Undo/Redo e Comandos Protobuf (Princípio VII)
- **Escolha**: O `ComandoAlterarPrimitivo` e o `CroquiModel` tratam valores `None` ou strings vazias chamando `ClearField` no objeto Protobuf, e preservam o valor/estado anterior para restaurar `HasField` e o dado durante o `undo()`.

## Risks / Trade-offs

- **[Risco]** Usuário apaga o texto por engano e o campo desaparece do YAML $\rightarrow$ **Mitigação**: O histórico de Undo (`Ctrl+Z`) reverte qualquer exclusão ou modificação imediatamente.
- **[Risco]** Campos obrigatórios que ficarem vazios podem causar erros de validação na compilação $\rightarrow$ **Mitigação**: A compilação já possui validadores claros que apontam erros com mensagens amigáveis na interface.
