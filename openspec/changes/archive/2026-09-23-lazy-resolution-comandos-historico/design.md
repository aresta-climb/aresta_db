## Context

Conforme descrito em `proposal.md`, os comandos de edição do editor (`ComandoEditor` e subclasses) realizavam navegação e validação ansiosa (*eager*) durante a deserialização (`deserializar()`) de comandos persistidos em `diario_salvo.bin` e `diario_pendente.bin`. Isso provocava falhas catastróficas durante o boot (`IndexError: list index out of range` em `navegar_para_mensagem` e `ValueError` em `validar_pertence_ao_croqui`), pois o modelo consolidado lido do disco pode não conter entidades temporárias ou índices que existiram em etapas intermediárias da sessão. Além disso, mutações em listas Protobuf geram novas instâncias em memória, tornando referências diretas de ponteiro (`self.msg`) obsoletas após operações de desfazer/refazer.

Restrições:
- Todos os nomes de métodos, logs, variáveis e documentação devem ser em português brasileiro (`AGENTS.md`).
- Cobertura de 100% em testes unitários com TDD (`_test.py`).
- Compatibilidade total com as chamadas de interface existentes que passam `msg` diretamente no construtor.

## Goals / Non-Goals

**Goals:**
- Implementar **Resolução Tardia (*Lazy Resolution*)** de mensagens alvo em `ComandoEditor`: armazenar `caminho_msg` e resolver a instância viva sob demanda via `_obter_msg()` apenas quando `undo()` ou `executar_redo()` forem chamados.
- Eliminar qualquer chamada a `navegar_para_mensagem` e `validar_pertence_ao_croqui` dentro dos métodos `deserializar()` de todos os comandos derivados de `ComandoEditor`.
- Prover navegação segura em `navegar_para_mensagem`: checagem estrita de limites de listas (`0 <= idx < len(lista)`) e validação de ramo ativo de `oneof` (`WhichOneof`), retornando `None` de forma segura sem disparar exceções não tratadas.
- Emitir erro legítimo (`logger.error`) se e somente se um comando for executado ou revertido e sua mensagem alvo não puder ser resolvida no caminho indicado.
- Tratar `LookupError` (que unifica `IndexError` e `KeyError`) em `carregar_diario_salvo` e `restaurar_do_diario` em `editor/core/historico.py`.

**Non-Goals:**
- Modificar o formato de serialização em disco do diário (a chave `"caminho_msg"` já existia nos dicionários serializados).
- Alterar o comportamento da interface do usuário (View) ou das assinaturas públicas de `CroquiModel`.
- Reescrever a lógica interna de comandos que não manipulam mensagens Protobuf diretamente (como `CmdSubstituirImagemMemoria`, que manipula apenas caminhos de arquivos em memória RAM).

## Decisions

### Decisão 1: Propriedade dinâmica `msg` com resolução tardia em `ComandoEditor`
- **Abordagem adotada**: `ComandoEditor` passa a ter a propriedade `msg` que invoca `_obter_msg()`. O método `_obter_msg()` utiliza `self.caminho_msg` e o modelo para localizar a mensagem no estado atual da árvore Protobuf. Caso `caminho_msg` não seja fornecido mas um objeto tenha sido atribuído a `_msg_cache`, ele é retornado (compatibilidade). Se a resolução falhar durante uma execução, registra `logger.error`.
- **Alternativas consideradas**:
  - *Manter ponteiros em cache e invalidar*: Complexo e sujeito a condições de corrida ao reordenar ou remover itens de coleções repetidas.
  - *Atualizar referências em toda mutação*: Requereria um observador global varrendo todos os comandos empilhados a cada alteração, com custo $O(N \times M)$ e alto acoplamento.

### Decisão 2: Construtores tolerantes aceitando `caminho_msg` opcional
- **Abordagem adotada**: Os construtores dos comandos (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, etc.) passam a aceitar `caminho_msg: Optional[str] = None`.
  - Quando instanciado pela View/Controller com `msg`, valida a pertinência (`validar_pertence_ao_croqui`) e armazena o caminho retornado em `self.caminho_msg`.
  - Quando instanciado por `deserializar()` com `caminho_msg`, atribui diretamente `self.caminho_msg = caminho_msg`, pulando `validar_pertence_ao_croqui`.
- **Alternativas consideradas**:
  - *Factory methods separados para deserialização*: Exigiria mudar o padrão de inicialização e criaria duplicidade de rotas de criação. Aceitar `caminho_msg` opcional no construtor mantém a API homogênea.

### Decisão 3: Tolerância estrutural em `navegar_para_mensagem`
- **Abordagem adotada**:
  - Para índices numéricos: testar `idx < len(atual)` antes de indexar.
  - Para campos de mensagem pertencentes a `oneof`: verificar `atual.WhichOneof(oneof.name) == parte`. Se outro ramo estiver ativo, abortar a navegação e retornar `None`.
  - Retornar `None` em qualquer anomalia estrutural em vez de lançar exceções.
- **Alternativas consideradas**:
  - *Lançar exceções customizadas (`CaminhoInvalidoError`)*: Exigiria blocos `try/except` em todas as chamadas de navegação no sistema. Retornar `None` permite verificação idêntica a ponteiro nulo (`if msg is None:`).

### Decisão 4: Captura de `LookupError` nos carregadores do diário
- **Abordagem adotada**: Em `historico.py`, atualizar as tuplas de exceções tratadas de `(ValueError, AttributeError, KeyError, TypeError)` para `(ValueError, AttributeError, LookupError, TypeError)`. Como `IndexError` e `KeyError` herdam de `LookupError`, qualquer erro residual de indexação ou chave ausente é capturado como aviso descartável em vez de exceção não tratada reportada ao Sentry.

## Risks / Trade-offs

- **[Risco] Tentativa de mutação com `msg is None` em comandos que não checam o retorno de `_obter_msg()`**:
  - *Mitigação*: Em `undo()` e `executar_redo()`, garantir checagem `if self.msg is None: return` (ou no `_obter_msg()`), registrando erro detalhado em `logger.error` e impedindo chamadas a métodos protegidos do modelo (`_set_primitivo`, `_adicionar_repeated`, etc.) com mensagem nula.
- **[Risco] Comandos compostos (`CmdRenomearEscalada`) com múltiplas referências**:
  - *Mitigação*: Armazenar lista de caminhos `caminhos_referencias`. Na execução de `undo()`/`executar_redo()`, filtrar referências que ainda existem (`[r for r in refs if r is not None]`), permitindo reverter com segurança as entidades que ainda se encontram presentes.
