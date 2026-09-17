## Context

No modelo Protobuf do Aresta, as referências nos mapas (`Mapa.Referencia`) conectam os IDs geométricos de POIs aos dados lógicos usando strings de nome (`ref.escalada`, `ref.setor`, `ref.grupo`). Veja `proposal.md` para a motivação detalhada da mudança.

Atualmente, o editor manipula a alteração de nomes de escaladas via `CmdAlterarPrimitivo`, que desconhece os mapas. Além disso, operações compostas em `mapas_controller.py` e `widget_editor_mapas.py` utilizavam `pilha.beginMacro()` nativo do Qt, cujos comandos C++ não implementam `.serializar()`, resultando em descarte silencioso pelo diário append-only (`diario_pendente.bin`).

## Goals / Non-Goals

**Goals:**
- Prover sincronização 100% transparente e atômica de referências em mapas ao renomear qualquer escalada no editor.
- Suportar digitação contínua a 60 FPS com mesclagem atômica (`mergeWith`), delimitada estritamente pelo ciclo de vida de foco do campo (`session_id`).
- Fornecer `CmdMacro(ComandoEditor)` com serialização completa e restaurável pelo `GerenciadorDiario`.
- Migrar todos os pontos que utilizavam `beginMacro`/`endMacro` do Qt para `CmdMacro`.
- Adicionar teste estático baseado em AST em `editor/arquitetura_mvc_test.py` proibindo `beginMacro`/`endMacro`.

**Non-Goals:**
- Renomeação em cascata de setores ou grupos (o foco deste change é a entidade `Escalada`, que é referenciada como ID de linha/POI).
- Modificação do schema do Protobuf ou introdução de UUIDs persistentes para entidades lógicas (mantém compatibilidade total com os schemas atuais e o `aresta_app`).
- Índices invertidos globais de referências com cache em memória (evita complexidade de sincronização e bugs de cache drift).

## Decisions

### 1. Comando Especializado `CmdRenomearEscalada` com `mergeWith` O(1)
- **Decisão**: Criar `CmdRenomearEscalada(ComandoEditor)` com campos `msg_escalada`, `nome_antigo`, `nome_novo` e `referencias`.
- **Racional**:
  - Na instanciação inicial (1º caractere digitado), executa a busca $O(N)$ no Pico e armazena os ponteiros das mensagens `croqui_pb2.Mapa.Referencia` afetadas.
  - Nas digitações subsequentes ininterruptas, `mergeWith()` apenas atualiza o `valor_novo` na escalada e nas referências já conhecidas em $O(K)$ (onde $K$ é tipicamente 1 ou 2 referências).
- **Alternativas consideradas**:
  - *Macro genérico a cada caractere*: Inviável para `mergeWith` contínuo; inflaria o histórico de Undo ou exigiria reconciliação complexa de árvores de subcomandos.

### 2. Delimitação de Sessão de Foco (`session_id`)
- **Decisão**: O `QLineEdit` de edição de nome em `WidgetEditorDados` gerencia um `session_id` que é incrementado a cada `focusInEvent` (ou seleção de nó). O `CmdRenomearEscalada` só aceita mesclar se `outro.session_id == self.session_id`.
- **Racional**: Garante que se o usuário alterar o nome, sair do campo, criar uma nova referência em um mapa e voltar ao campo, o editor executará uma nova busca limpa a partir do estado atual da árvore sem reutilizar a lista anterior.
- **Alternativas consideradas**:
  - *Baseado em tempo/timeout*: Frágil e não determinístico, podendo causar mesclagens indesejadas se o usuário pausar a digitação.

### 3. Biblioteca Autônoma de Resolução Simétrica de Escopo (`referencias_util.py`)
- **Decisão**: Isolar a lógica de correlação em funções puras em `editor/models/referencias_util.py` (Princípio II - Library-First):
  - `setor_efetivo = ref.setor if ref.setor else mapa_setor_nome`
  - `grupo_efetivo = ref.grupo if ref.grupo else mapa_grupo_nome`
- **Racional**: Espelha a arquitetura comprovada do `DatasetResolver` do `aresta_app`, suportando mapas de setor (com setor/grupo implícito), mapas entre setores, mapas de grupo e mapas gerais de pico.
- **Alternativas consideradas**:
  - *Comparar apenas o nome da escalada*: Causaria colisões incorretas caso dois setores distintos possuíssem uma via homônima (ex: "Via Normal").

### 4. `CmdMacro` e Banimento de `beginMacro`/`endMacro`
- **Decisão**: Implementar `CmdMacro(ComandoEditor)` com serialização recursiva de subcomandos via `deserializar_comando` e criar teste de AST em `editor/arquitetura_mvc_test.py` proibindo `beginMacro`/`endMacro`.
- **Racional**: Garante que operações agrupadas sejam gravadas com integridade no `diario_pendente.bin`, permitindo recuperação de sessão após falhas inesperadas sem perda de dados.
- **Alternativas consideradas**:
  - *Tentar serializar a classe C++ interna do Qt*: O PySide6 não expõe hooks para injetar métodos Python na classe interna gerada por `beginMacro`.

## Risks / Trade-offs

- **[Risco] Nome vazio durante edição**: O usuário pode temporariamente apagar todo o texto no campo.
  - *Mitigação*: `CmdRenomearEscalada` lida com string vazia limpando o campo via `ClearField` conforme padrão do `CroquiModel`, e ao digitar novamente restaura o valor em `mergeWith`.
- **[Risco] Escaladas aninhadas em enfiadas**: Vias de múltiplas enfiadas possuem sub-escaladas em `via.enfiadas`.
  - *Mitigação*: `referencias_util.py` percorre recursivamente tanto as escaladas do setor quanto as enfiadas de `ViaMultiplasEnfiadas`.
- **[Risco] Performance de varredura no 1º caractere**:
  - *Mitigação*: O número total de referências por pico raramente excede 500 itens. A varredura em memória RAM em Python leva menos de 0,05 ms, garantindo frame time abaixo de 16 ms.

## Migration Plan

1. Criar e testar `referencias_util.py` de forma independente com 100% de cobertura.
2. Implementar `CmdMacro` e `CmdRenomearEscalada` em `editor/commands/comandos_protobuf.py` com registro em `deserializar_comando`.
3. Migrar `mapas_controller.py` e `widget_editor_mapas.py` de `beginMacro`/`endMacro` para `CmdMacro`.
4. Adicionar a regra proibitiva em `editor/arquitetura_mvc_test.py`.
5. Integrar no `CroquiController` e `WidgetEditorDados` com suporte a `session_id`.
6. Validar com testes de integração e unitários completos.
