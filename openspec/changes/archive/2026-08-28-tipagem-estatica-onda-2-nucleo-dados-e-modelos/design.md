# Design Técnico: Onda 2 - Tipagem Estática do Núcleo de Dados, Modelos e Core

## Context

O pacote `editor/core/` é a espinha dorsal de funcionamento do Editor Aresta. Ele engloba a persistência em disco (`storage.py`), parsing de contexto (`contexto.py`), transformações espaciais (`coordenadas.py`, `geometrias_poi.py`), representação de workspace (`workspace.py`), autenticação e envio de propostas (`cliente_auth_supabase.py`, `servico_submissao.py`), pilha de undo/redo (`historico.py`), diário de comandos (`diario.py`) e telemetria silenciosa (`telemetria.py`). 

A Onda 2 visa conferir rigidez e confiabilidade estática a todos esses 21 arquivos centrais e seus testes, eliminando retornos implícitos de `None` e variáveis com tipo `Any`.

## Goals / Non-Goals

**Goals:**
- Anotar 100% das funções, métodos, atributos de classe e variáveis públicas em todos os módulos de `editor/core/`.
- Garantir `None-safety` estrita: todo valor que possa ser `None` deve ser explicitamente tipado como `T | None` ou `Optional[T]` e devidamente tratado com verificações antes do acesso.
- Garantir que todos os arquivos de `editor/core/` passem sem erros no `mypy --strict`.
- Expandir o teste guardião `tests/tipagem_estatica_test.py` para incluir o diretório `editor/core/`.
- Manter 100% de cobertura de testes unitários em toda a suíte de testes.

**Non-Goals:**
- Tipar os componentes de interface gráfica do PySide6 (`editor/views/`, `editor/legacy_views/`), que dependem do core e serão tipados na Onda 4.
- Tipar os comandos e controladores (`editor/commands/`, `editor/controllers/`), que serão tipados na Onda 3.

## Decisions

### 1. Organização dos Tipos no Core por Pacotes Lógicos
- **Decisão**: Tipar os módulos em subgrupos coesos e dependentes:
  1. *Fundação e Formatação*: `version.py`, `formatacao.py`, `contexto.py`, `coordenadas.py`, `geometrias_poi.py`, `storage.py`.
  2. *Workspace e Modelos*: `workspace.py`, `croqui_format.py`, `croqui_experimental.py`, `proto_comments.py`, `imagens_markdown.py`, `processamento_imagem_campo.py`.
  3. *Sessão, Rede e Submissão*: `gerenciador_sessao.py`, `cliente_auth_supabase.py`, `servico_submissao.py`, `servico_loja.py`, `sync.py`, `worker.py`.
  4. *Histórico e Telemetria*: `historico.py`, `diario.py`, `telemetria.py`, `registro_log.py`.
- **Razão**: Permite validação incremental de dependências sem criar ciclos de tipos.

### 2. Integração ao Teste Guardião do Pytest
- **Decisão**: O teste `tests/tipagem_estatica_test.py` passa a verificar explicitamente todos os arquivos `.py` de `editor/core/` via MyPy e AST.
- **Razão**: Impede regressões automáticas no CI e durante o desenvolvimento das próximas ondas.

## Risks / Trade-offs

- **[Risco]** Módulos de `editor/core/` que recebem mensagens Protobuf podem ter tipagem incompatível se não usarem os stubs `.pyi` gerados na Onda 1.
  - **Mitigação**: Os stubs `croqui_pb2.pyi`, `beta_pb2.pyi`, etc. gerados na Onda 1 já estão disponíveis e fornecem anotações precisas para todos os campos.
- **[Risco]** Classes que herdavam de `QObject` ou usavam sinais PySide6 (`Signal`, `Slot`) no `worker.py` ou `atualizador_ui.py`.
  - **Mitigação**: Tipar sinais com argumentos estritos (ex: `Signal(str)`, `Signal(int, int)`) e decorar slots com `@Slot()`.
