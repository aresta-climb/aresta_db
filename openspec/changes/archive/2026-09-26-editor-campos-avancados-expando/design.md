## Context

Atualmente, `WidgetFormularioPadrao` renderiza todos os campos de uma mensagem do Protobuf sequencialmente de cima para baixo dentro de um `QScrollArea`. Mensagens densas como `ViaEsportiva`, `ViaMultiplasEnfiadas`, `Setor` e `Croqui` possuem muitos campos técnicos (ex: graus artificiais, tipos de ancoragem, chave Pix, datas de manutenção) que não são necessários para o preenchimento inicial básico.

Consulte [proposal.md](proposal.md) para a motivação detalhada e [spec.md](specs/editor-dados-formularios/spec.md) para os requisitos de comportamento.

## Goals / Non-Goals

**Goals:**
- Estender `google.protobuf.FieldOptions` com `bool avancado = 50013` em `croqui.proto`.
- Anotar os campos técnicos/secundários das principais entidades do croqui (`ViaEsportiva`, `ViaMovel`, `Boulder`, `ViaMultiplasEnfiadas`, `Highline`, `Setor`, `Pico`, `Croqui`), mantendo `nome`, `dificuldade`, `extensao`, `conquistadores`, `data_abertura`, `destaque` e `descricao` como campos principais.
- Adaptar o fluxo de renderização de `WidgetFormularioPadrao._render_message_fields` para segregar campos principais de campos avançados.
- Renderizar campos avançados dentro de um contêiner colapsável estilizado no rodapé dos campos principais, antes dos cartões de subelementos.
- Exibir contagem dinâmica no cabeçalho colapsado: `▶ Opções Avançadas (X preenchidos de Y)` ou `▶ Opções Avançadas (Y campos)`.
- Reter a preferência de expansão em memória (`_campos_avancados_expandidos`) para que ao navegar entre entidades na mesma sessão o estado seja preservado.
- Garantir 100% de compatibilidade com Undo/Redo e sincronização reativa do `CroquiModel`.

**Non-Goals:**
- Persistir o estado do expando em disco / arquivo de preferências além da sessão em execução.
- Alterar campos de mensagens que já são invisíveis (`INVISIVEL`) ou editadas em telas dedicadas (`MAPA`, `COORDENADA`).
- Alterar a estrutura de nós da árvore lateral (`ArvoreDadosTreeView`).

## Decisions

### 1. Extensão de FieldOptions no Protobuf (`croqui.proto`)
- **Escolha**: Definir `bool avancado = 50013;` diretamente em `extend google.protobuf.FieldOptions`.
- **Por que**: Segue o padrão arquitetural do Aresta onde toda a semântica da UI (`texto_na_ui`, `formato_na_ui`, `titulo_na_ui`, etc.) é governada de forma declarativa e fortemente tipada pelo schema do Protobuf.
- **Alternativas consideradas**: Dicionário de configuração estático no Python (`CAMPOS_AVANCADOS = {...}`). Rejeitado por espalhar metadados do domínio fora do schema e dificultar manutenção e testes.

### 2. Renderização Síncrona dos Widgets Avançados (Visibilidade via `setVisible`)
- **Escolha**: Instanciar os cards dos campos avançados no momento de criação do formulário e agrupá-los em um `QFrame` interno cuja visibilidade é alternada via `setVisible(True/False)`.
- **Por que**: O `WidgetFormularioPadrao` escuta sinais do modelo (`campo_alterado`, `repeated_item_alterado`, etc.) e localiza os widgets via `findChildren(QWidget)` inspecionando `protobuf_field` e `protobuf_msg_id`. Se a renderização fosse lazy (tardia), um evento de Undo/Redo enquanto o expando estivesse fechado não encontraria o widget correspondente para atualizar seu valor. Com a criação síncrona, todos os widgets existem na árvore de objetos Qt e se mantêm 100% sincronizados.
- **Alternativas consideradas**: Lazy loading no primeiro clique de expansão. Rejeitado devido ao risco de perda de sincronização durante operações de Undo/Redo antes da primeira abertura.

### 3. Algoritmo de Verificação de Campos Preenchidos
- **Escolha**: Criar função auxiliar `_campo_esta_preenchido(msg, field)`:
  - Para campos repetidos (`field.is_repeated`): preenchido se `len(getattr(msg, field.name)) > 0`.
  - Para submensagens (`TYPE_MESSAGE`): preenchido se `msg.HasField(field.name)`.
  - Para primitivos: verifica se `msg.HasField(field.name)` (quando suportado) ou se o valor atual difere do valor padrão do tipo (string não vazia, int != 0 e != SpinBoxVazio.VALOR_NULO, float != 0.0, bool != None).
- **Por que**: Permite atualizar dinamicamente o contador do cabeçalho colapsado, informando ao usuário quantos campos avançados já possuem conteúdo.

### 4. Gestão de Estado de Sessão Compartilhado
- **Escolha**: Armazenar o booleano `_campos_avancados_expandidos` na instância do `WidgetEditorDados` (ou `WidgetFormularioPadrao`) e consultar este valor ao inicializar a visibilidade da seção colapsável.
- **Por que**: Garante que se o usuário abrir as opções avançadas em uma via, ao clicar na próxima via a seção já apareça aberta, eliminando cliques repetitivos em sessões de edição intensa.

## Risks / Trade-offs

- **[Regeneração de Stubs do Protobuf]** → A adição de `avancado` no `.proto` exige regeneração de `croqui_pb2.py`.  
  *Mitigação*: Executar a ferramenta de compilação oficial do repositório (`python -m aresta_api.scripts.compilar_proto` ou script equivalente) e rodar a suíte inteira de testes automatizados para verificar ausência de quebras.
- **[Largura e Rolagem do Formulário]** → Campos avançados abertos aumentam a extensão vertical do formulário.  
  *Mitigação*: O `WidgetFormularioPadrao` já opera dentro de um `QScrollArea` com `setWidgetResizable(True)`, acomodando naturalmente qualquer altura adicional.
