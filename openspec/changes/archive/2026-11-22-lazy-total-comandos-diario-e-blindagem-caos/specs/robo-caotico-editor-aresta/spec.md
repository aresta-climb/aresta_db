# Spec Delta

## MODIFIED Requirements

### Requirement: Fuzzing de Entradas em Formulários, Árvore, Imagens e Mapas
O motor SHALL sortear e aplicar ações de fuzzing sobre os componentes interativos visíveis das abas de Dados, Imagens, Mapas, Betas e barras de ferramentas, incluindo entradas de texto hostis, alternância de seletores `oneof`, adições e remoções estruturais em listas `repeated`, manipulações na árvore Protobuf, traçados na cena gráfica 2D, salvamentos, recarregamentos completos de sessão do croqui a partir do disco e rajadas de desfazer/refazer.

#### Scenario: Injeção de entradas fuzz em campos de formulário e coordenadas
- **WHEN** o motor seleciona um campo de texto, numérico ou coordenada E7 visível no formulário de dados
- **THEN** o motor SHALL injetar valores sorteados do dicionário de fuzzing (textos vazios, strings longas sem espaços, emojis compostos, delimitadores YAML/Markdown, links de referência quebrados ou coordenadas limítrofes) e confirmar a edição.

#### Scenario: Interação caótica em cena vetorial de mapas e editor de imagens
- **WHEN** a aba de Mapas ou de Imagens estiver ativa durante a exploração
- **THEN** o motor SHALL sortear cliques, arrastes de mouse, mudanças de ferramentas de desenho/corte/máscara e ajustes de controles deslizantes sobre a cena gráfica.

#### Scenario: Rajadas de desfazer e refazer intercaladas com edições
- **WHEN** a pilha de histórico possuir comandos empilhados durante a exploração
- **THEN** o motor SHALL sortear ações simples e rajadas consecutivas de `Undo` e `Redo` intercaladas com trocas de abas e salvamentos.

#### Scenario: Ciclo completo de mutações estruturais, salvamento, reabertura de sessão e reversão
- **WHEN** o motor sorteia ações estruturais (adição/remoção de itens `repeated` ou troca de variante `oneof`) seguidas de salvamento e ação de recarregar a sessão do croqui
- **THEN** o motor SHALL reabrir o croqui a partir do disco (exercitando `carregar_diario_salvo` e eventual `restaurar_do_diario`), ressincronizar os hashes de simetria dos passos recarregados e permitir que passos subsequentes de `Undo` e `Redo` validem a reversão pós-reabertura sem erros de log ou quebra de simetria.

### Requirement: Oráculos de Exceção, Simetria de Undo/Redo e Integridade do Diário
A cada passo executado, o motor SHALL verificar três oráculos independentes: ausência de exceções não tratadas, logs de erro (`ERROR`/`CRITICAL`) em qualquer logger Python do processo (*root logger* e `aresta_editor`) ou objetos C++ deletados, simetria determinística do estado Protobuf na pilha de `Undo`/`Redo` e integridade estrutural e semântica do diário binário de sessão (incluindo deserialização real de cada comando persistido), garantindo que toda falha detectada possua um *traceback* real da pilha de execução no ponto da verificação.

#### Scenario: Detecção de exceção em slot Qt ou objeto C++ já deletado
- **WHEN** um slot Qt, temporizador ou thread em segundo plano lança uma exceção não tratada (como `RuntimeError: Internal C++ object already deleted`)
- **THEN** o oráculo de exceções SHALL capturar imediatamente a exceção original com seu *traceback* completo, interrompendo a semente atual e registrando a falha.

#### Scenario: Detecção de erro registrado no logger da aplicação
- **WHEN** qualquer módulo da aplicação ou thread em segundo plano emite um registro de nível `ERROR` ou `CRITICAL` (tanto sob `aresta_editor` quanto no *root logger*)
- **THEN** o oráculo SHALL interceptar o registro (extraindo `exc_info` quando presente ou levantando uma exceção real com *traceback* no ponto do log), interromper a semente atual e tratá-la como falha reproduzível para encolhimento e envio ao Sentry.

#### Scenario: Detecção de quebra de simetria na pilha de Undo/Redo
- **WHEN** o motor executa `Undo` ou `Redo` para um índice da pilha de histórico previamente visitado (sem salvamento modificador intermediário) e a serialização determinística do Protobuf diverge do hash registrado naquele índice
- **THEN** o oráculo de simetria SHALL levantar e capturar uma `AssertionError` com *traceback* completo da pilha de chamadas, reportando a falha de corrupção de estado ou mutação fora de comando de histórico.

#### Scenario: Verificação de integridade do diário transacional
- **WHEN** comandos são gravados no diário pendente ou consolidados no diário salvo durante a sessão
- **THEN** o oráculo de diário SHALL validar que os arquivos binários do diário permanecem legíveis até o `EOF` e que cada registro pode ser reconstruído por `deserializar_comando` sem levantar exceção e sem emitir logs `ERROR`, reportando falha com *traceback* completo caso detecte corrupção ou efeito colateral de erro.
