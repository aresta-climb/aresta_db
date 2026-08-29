# Design Técnico: Tipagem Estática Estrita - Onda 4: Views e UI PySide6

## Context

Com a conclusão das Ondas 1 (Infra/Tooling), 2 (Core/Dados) e 3 (Commands/Controllers), o núcleo de dados, modelos e comandos está 100% tipado e protegido por testes. A Onda 4 cobre as interfaces visuais do Aresta Editor (`editor/views/`, `editor/views/dialogos/`, `editor/legacy_views/`, `editor/models/` e `editor/main.py`), eliminando incertezas de tipo nas classes Qt (`QWidget`, `QDialog`, `QTreeWidget`, etc.), slots de eventos, delegates e factories dinâmicas de campos Protobuf.

## Goals / Non-Goals

**Goals:**
- Anotar 100% dos módulos de `editor/views/`, `editor/views/dialogos/`, `editor/legacy_views/`, `editor/models/` e `editor/main.py` com tipos estritos compatíveis com MyPy (`strict = true`).
- Tratar rigorosamente sinais e slots do PySide6 (`Signal`, `Slot`), garantindo tipos nos argumentos de sinal e assinaturas dos métodos emissores/receptores.
- Garantir coerção segura em `protobuf_widget_factory.py` e adaptadores de árvore (`tree_view_adapter.py`).
- Manter 100% de aprovação na suíte de testes unitários e de integração (`pytest`).
- Expandir o teste guardião `tests/tipagem_estatica_test.py` com metatestes AST e MyPy para toda a Onda 4.

**Non-Goals:**
- Refatorar regras de negócio ou alterar o layout/estilo visual da interface de usuário.
- Modificar scripts de automação de serving, ingestão ou CI global (reservados para a Onda 5).

## Decisions

### 1. Tipagem em Classes e Widgets PySide6
- **Decisão:** Assinaturas de inicializadores `__init__(self, ..., parent: Optional[QWidget] = None) -> None` e métodos de ciclo de vida Qt com anotações explícitas de widgets e layouts.
- **Alternativa Considerada:** Usar anotações genéricas `parent: Any`. Descartado para obter o benefício máximo de segurança de tipos onde possível.

### 2. Tratamento de Delegates e Fábricas Dinâmicas Protobuf
- **Decisão:** Em `protobuf_widget_factory.py`, especificar tipos de retorno (`QWidget`, `tuple[QWidget, Callable[..., None]]`) e anotar explicitamente callables, dicionários de factories e lambdas.
- **Alternativa Considerada:** Tratar retorno como `Any`. Descartado para garantir previsibilidade na criação de widgets por tipo de campo.

### 3. Integração com Teste Guardião
- **Decisão:** Criar `ARQUIVOS_ONDA_4` em `tests/tipagem_estatica_test.py` com checagem MyPy e AST.

## Risks / Trade-offs

- **[Risco]** Colisão de nomes ou sobrecarga de assinaturas em herança de classes Qt (ex: `paintEvent`, `mousePressEvent`, `resizeEvent`).
  - *Mitigação:* Usar tipos estritos compatíveis com o PySide6 (`QPaintEvent`, `QMouseEvent`, `QResizeEvent`, etc.) e rodar MyPy localmente em cada arquivo antes de avançar.
- **[Risco]** Views legadas (`editor/legacy_views/area_principal.py`, etc.) com acoplamento a modelos dinâmicos.
  - *Mitigação:* Anotar métodos com segurança defensiva e validação de `None`, preservando a lógica existente.
