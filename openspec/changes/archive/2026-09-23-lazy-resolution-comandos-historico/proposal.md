## Why

Durante a inicialização do editor (`InicializacaoEditor`), erros críticos foram reportados no Sentry (`list index out of range` em `aresta_editor.historico`). A causa raiz é o acoplamento precoce (eager) na instanciação e deserialização dos comandos de Undo/Redo (`ComandoEditor`): ao carregar o diário salvo (`diario_salvo.bin`), o sistema tenta navegar imediatamente pela árvore Protobuf para obter referências vivas (`msg`), disparando `IndexError` ou rejeições de nós órfãos quando a estrutura atual difere de passos intermediários do diário. Além disso, quando itens repetidos são removidos e reinseridos no `undo()`, novas instâncias Protobuf são criadas em memória, tornando referências diretas de ponteiro (`self.msg`) obsoletas.

É necessário migrar a resolução de mensagens alvo nos comandos para o padrão de Resolução Tardia (*Lazy Resolution*) baseado em `caminho_msg`, resolvendo a entidade real no momento da invocação de `undo()` ou `executar_redo()`. Com isso, o boot torna-se limpo, determinístico e imune a erros espúrios, e qualquer falha na localização do alvo durante um `undo()` passa a ser um erro real e legítimo.

## What Changes

- **Resolução Tardia de Mensagens Alvo**: Comandos derivados de `ComandoEditor` passam a armazenar `caminho_msg` como fonte canônica do alvo, postergando a resolução e validação da mensagem no modelo para o momento da execução (`undo()` e `executar_redo()`).
- **Deserialização Declarativa e Segura**: Os métodos `deserializar()` dos comandos de `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_mapas.py` não realizam mais navegação ansiosa (`navegar_para_mensagem`) ou validação de pertencimento à árvore durante a carga, recebendo `caminho_msg` diretamente dos dados persistidos.
- **Detecção de Falha Legítima na Reversão**: Se no momento de executar `undo()` ou `executar_redo()` a mensagem alvo no caminho não existir ou estiver inconsistente, o comando registra um erro legítimo (`logger.error`) e notifica a falha de reversão.
- **Navegação Segura em Limites de Lista e Oneofs**: A função `navegar_para_mensagem` passa a validar limites de listas repetidas (retornando `None` ou levantando erro controlado em vez de `IndexError` bruto) e a respeitar o ramo ativo de mensagens `oneof` (não retornando mensagens dummy/fantasma quando o ramo estiver inativo).
- **Tratamento de Exceções em Diário no Boot**: `historico.carregar_diario_salvo` e `historico.restaurar_do_diario` passam a capturar `LookupError` (cobrindo `IndexError` e `KeyError`) junto a `ValueError, AttributeError, TypeError`, prevenindo que inconsistências residuais de sessões passadas poluam o Sentry como erros não tratados durante a inicialização.

## Capabilities

### Modified Capabilities
- `undo-redo-protobuf`: Adiciona requisito de Resolução Tardia (Lazy Resolution) de mensagens alvo via `caminho_msg` e atualização da Guarda de Integridade para diferenciar validação ao vivo vs deserialização.
- `editor-diario-recuperacao`: Adiciona requisito de resiliência a erros de índice e busca (`LookupError`) no carregamento de comandos do diário no boot.

## Impact

- `editor/commands/comandos_protobuf.py`: Comandos (`CmdAlterarPrimitivo`, `CmdAlterarRepeatedItem`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, etc.) e funções utilitárias (`navegar_para_mensagem`, `validar_pertence_ao_croqui`).
- `editor/commands/comandos_mapas.py`: `CmdAdicionarMapaArquivo` adota a mesma resolução tardia.
- `editor/core/historico.py`: Tratamento de exceções em `carregar_diario_salvo` e `restaurar_do_diario`.
- Testes unitários em `editor/commands/comandos_protobuf_test.py`, `editor/commands/comandos_mapas_test.py` e `editor/core/historico_test.py`.
