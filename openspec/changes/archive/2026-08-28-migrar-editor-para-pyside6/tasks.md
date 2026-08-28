# Tarefas: Migração do Editor Aresta para PySide6

## 1. Configuração do Ambiente e Dependências

- [x] 1.1 Atualizar `pyproject.toml` substituindo `pyqt6` por `pyside6` no grupo de dependências `editor`
- [x] 1.2 Atualizar `editor/build.py` para importar e utilizar PySide6 na rotina de geração de ícones e empacotamento

## 2. Testes em Primeiro Lugar - Ciclo TDD (Red)

- [x] 2.1 Atualizar testes de integração do ciclo de vida da interface e arquitetura MVC (`editor/arquitetura_mvc_test.py`, `editor/legacy_views/area_principal_conexao_test.py`, `editor/legacy_views/dialogo_conexao_celular_test.py`) para o backend PySide6
- [x] 2.2 Atualizar testes unitários do Core do Editor (`editor/core/*_test.py`) com imports e mocks (`unittest.mock.patch`) direcionados a `PySide6`
- [x] 2.3 Atualizar testes unitários de Comandos, Modelos e Controladores (`editor/commands/*_test.py`, `editor/models/*_test.py`, `editor/controllers/*_test.py`)
- [x] 2.4 Atualizar testes unitários das Views (`editor/views/*_test.py`, `editor/legacy_views/*_test.py`) e de Curadoria (`coleta_de_betas/curadoria/*_test.py`)

## 3. Migração do Código de Produção (Green)

- [x] 3.1 Migrar módulos de `editor/core/` (`historico.py`, `monitor_inatividade.py`, `servidor_celular.py`, `servidor_oauth_callback.py`, `storage.py`, `worker.py`, `atualizador_ui.py`, `servico_loja.py`) para `PySide6` com primitivas `Signal` e `Slot`
- [x] 3.2 Migrar modelos em `editor/models/` para `PySide6`
- [x] 3.3 Migrar comandos em `editor/commands/` utilizando `PySide6.QtGui.QUndoCommand` e preservando a regra de mutação de estado via pilha de histórico
- [x] 3.4 Migrar controladores em `editor/controllers/` para `PySide6`
- [x] 3.5 Migrar componentes de interface em `editor/views/`, `editor/legacy_views/` e ponto de entrada `editor/main.py`
- [x] 3.6 Migrar módulo de curadoria em `coleta_de_betas/curadoria/` (`carregador_imagens.py`, `painel_curadoria.py`)

## 4. Validação de Cobertura, Documentação e Empacotamento (Refactor)

- [x] 4.1 Executar a suíte de testes com `pytest` e verificar 100% de cobertura nos testes unitários e de integração
- [x] 4.2 Verificar conformidade de nomes, variáveis e comentários 100% em português brasileiro
- [x] 4.3 Executar validação de build do executável standalone via `editor/build.py`
