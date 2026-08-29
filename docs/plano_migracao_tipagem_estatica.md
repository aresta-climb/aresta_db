# Plano Mestre de Migração para Tipagem Estática Estrita (5 Ondas)

Este documento estabelece o plano abrangente de modernização e blindagem de código do repositório Aresta Climb através da adoção de **Tipagem Estática Estrita (Strict Static Typing)** em Python 3.13 com `mypy`, stubs tipados para Protobuf (`mypy-protobuf`), tipagem de sinais e slots em PySide6 e testes automatizados no `pytest`.

---

## 1. Motivação e Objetivos

O editor e as ferramentas do repositório processam estruturas de dados complexas (Protobuf, YAML, SQLite, APIs e nós de interface gráfica). A ausência de tipagem estática e de verificação em tempo de compilação/CI propiciava crashes em produção por:
- Acesso a atributos em variáveis `None` (`AttributeError: 'NoneType' object has no attribute 'x'`).
- Argumentos com tipos trocados ou ausência de argumentos obrigatórios.
- Incompatibilidade entre sinais Qt e seus slots receptores.
- Inconsistências de nomenclatura em mensagens Protobuf e dicionários dinâmicos.

### Metas Estratégicas
1. **Zero Bugs de Tipagem em Produção**: Eliminar 100% dos erros clássicos de `NoneType` e incompatibilidade de tipos.
2. **Garantia de Não-Regressão**: Testes automatizados na suíte padrão (`pytest`) que falham se qualquer código for submetido sem tipagem ou com violações de tipos.
3. **Autocompletação e Produtividade**: Stubs `.pyi` para mensagens Protobuf e componentes PySide6 para agilidade e segurança no desenvolvimento.

---

## 2. Visão Geral das 5 Ondas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROTEIRO DE MIGRAÇÃO EM 5 ONDAS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ONDA 1: Infraestrutura, Tooling & Testes Guardiões                         │
│  ├── Configuração de MyPy estrito e pacotes de tipos no pyproject.toml      │
│  ├── Geração de .pyi stubs para Protobuf (mypy-protobuf na aresta_api)      │
│  └── Testes automatizados de conformidade de tipos no Pytest                │
│                                                                             │
│  ONDA 2: Núcleo de Dados, Modelos & Base                                    │
│  ├── aresta_api/ (módulos Python e serializadores)                          │
│  ├── database/ (estruturas de dados e parsers)                              │
│  └── editor/core/ (storage, sessão, workspace, telemetria, coordenadas)     │
│                                                                             │
│  ONDA 3: Lógica de Aplicação, Comandos & Controladores                      │
│  ├── editor/commands/ (comandos protobuf, mapas, dados, undo/redo)          │
│  └── editor/controllers/ (croqui, mapas, compilação, publish)               │
│                                                                             │
│  ONDA 4: Interface do Usuário (PySide6 UI Layer)                            │
│  ├── editor/views/ e editor/legacy_views/                                   │
│  ├── editor/widgets/ e editor/dialogs/                                      │
│  └── Sinais (Signal) e Slots (@Slot) fortemente tipados                     │
│                                                                             │
│  ONDA 5: Módulos de Suporte, Scripts & Ativação Global                      │
│  ├── coleta_de_betas/, serving/, migracoes/ e scripts/                      │
│  └── Ativação do modo --strict global permanente no CI e pre-commit         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detalhamento das 5 Ondas

### Onda 1: Infraestrutura, Tooling & Testes Guardiões
**Escopo e Foco:**
- Inclusão das dependências de desenvolvimento no `pyproject.toml` (`mypy`, `mypy-protobuf`, `types-requests`, `types-PyYAML`, `types-protobuf`).
- Configuração do `[tool.mypy]` com flags estritas (`strict = true`, `disallow_untyped_defs = true`, `check_untyped_defs = true`, `no_implicit_optional = true`, `warn_return_any = true`).
- Integração do plugin `protoc-gen-mypy` ao pipeline de compilação de protos em `aresta_api/build.py` para gerar arquivos `.pyi` para todos os arquivos `.proto`.
- Criação do teste guardião no Pytest (`tests/tipagem_estatica_test.py`) que executa `mypy` e um validador de AST para impedir commits sem tipagem.

### Onda 2: Núcleo de Dados, Modelos & Base
**Escopo e Foco:**
- Tipagem completa de `aresta_api/` (geradores, validadores, serializadores).
- Tipagem de `database/` (manipuladores de banco de dados e modelos).
- Tipagem de `editor/core/`:
  - `storage.py`, `contexto.py`, `coordenadas.py`, `workspace.py`.
  - `gerenciador_sessao.py`, `cliente_auth_supabase.py`.
  - `telemetria.py` e `historico.py`.

### Onda 3: Lógica de Aplicação, Comandos & Controladores
**Escopo e Foco:**
- Tipagem estrita de `editor/commands/`:
  - `comandos_protobuf.py`, `comandos_mapas.py`, `comandos_dados.py`.
- Tipagem de `editor/controllers/`:
  - `croqui_controller.py`, `mapas_controller.py`, `compilacao_controller.py`, `publish_controller.py`.
- Garantia de contratos de tipo entre a pilha de histórico `QUndoStack` e as mutações do modelo.

### Onda 4: Interface do Usuário (PySide6 UI Layer)
**Escopo e Foco:**
- Tipagem de todas as telas em `editor/views/` (`tela_de_abertura.py`, `widget_editor_dados.py`, `widget_editor_mapas.py`, etc.).
- Tipagem de telas legadas e widgets auxiliares (`editor/legacy_views/`, `editor/widgets/`).
- Tipagem explícita de sinais Qt (`Signal(...)`) com tipos primitivos ou modelos de dados bem definidos.
- Decoração de todos os métodos callbacks com `@Slot(...)`.

### Onda 5: Módulos de Suporte, Scripts & Ativação Global
**Escopo e Foco:**
- Tipagem de `coleta_de_betas/` (extratores, curadoria, runner).
- Tipagem de `serving/` (APIs e validadores).
- Tipagem de `scripts/` e rotinas de build/release.
- Ativação da flag global de verificação de tipos estrita no CI/CD (`uv run mypy .`).

---

## 4. Governança e Regras de Qualidade

1. **Princípio da Não-Regressão**: Uma vez que um módulo é tipado e passa pelo MyPy, ele nunca mais poderá ter type ignores desnecessários ou perder anotações.
2. **Proibição de `Any` Indiscriminado**: O uso de `Any` deve ser estritamente excepcional e justificado com comentário técnico.
3. **100% Test Coverage**: Novos testes de tipagem e todas as refatorações mantêm 100% de cobertura de código.
