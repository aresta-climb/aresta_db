# Tasks: Migração do Editor Aresta para PySide6

## 1. Atualização de Dependências e Configuração

- [ ] 1.1 Atualizar `pyproject.toml` substituindo `pyqt6` por `pyside6` no grupo `editor`
- [ ] 1.2 Atualizar `editor/build.py` para importar e utilizar PySide6 na rotina de geração de ícones e empacotamento

## 2. Migração do Core, Models e Comandos do Editor

- [ ] 2.1 Atualizar imports e sinais (`Signal`, `Slot`) nos módulos de `editor/core/` (`historico.py`, `monitor_inatividade.py`, `servidor_celular.py`, `servidor_oauth_callback.py`, `storage.py`, `worker.py`, `atualizador_ui.py`, `servico_loja.py`)
- [ ] 2.2 Atualizar imports e sinais nos modelos em `editor/models/`
- [ ] 2.3 Atualizar imports e comandos `QUndoCommand` em `editor/commands/`

## 3. Migração dos Controllers e Views do Editor

- [ ] 3.1 Atualizar imports e sinais nos controladores em `editor/controllers/`
- [ ] 3.2 Atualizar imports e widgets nas visualizações em `editor/views/` e `editor/legacy_views/`
- [ ] 3.3 Atualizar `editor/main.py` e ponto de entrada da aplicação

## 4. Migração de Módulos Auxiliares e Curadoria

- [ ] 4.1 Atualizar imports e sinais em `coleta_de_betas/curadoria/` (`carregador_imagens.py`, `painel_curadoria.py`)
- [ ] 4.2 Atualizar referências conceituais e de documentação em `docs/`

## 5. Atualização da Suíte de Testes e Validação

- [ ] 5.1 Atualizar imports, fixtures e mocks (`unittest.mock.patch`) em todos os arquivos `*_test.py`
- [ ] 5.2 Executar a suíte de testes do editor com `pytest` e validar 100% de sucesso
- [ ] 5.3 Validar empacotamento ou execução do editor via `editor/build.py`
