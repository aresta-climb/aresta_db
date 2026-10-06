# Tasks

## 1. Limpeza do PyInstaller no Linux em `editor/build.py`

- [x] 1.1 Remover função `filtrar_binarios_desnecessarios` e heurísticas manuais de exclusão de bibliotecas `.so` em `editor/build.py`, verificando que nenhuma lógica de exclusão de Linux permaneça no script
- [x] 1.2 Atualizar `editor/build_test.py` removendo testes legados de filtragem de `.so` e garantindo que a suíte passe com 100% de cobertura de código em `editor/build.py`

## 2. Orquestração do Flatpak no `editor/build.py dist`

- [x] 2.1 Escrever testes unitários em `editor/build_test.py` simulando execução do comando `dist` no Linux, verificando a chamada a `flatpak-builder` e o tratamento de erro amigável quando a ferramenta não estiver instalada
- [x] 2.2 Implementar a função `orquestrar_build_flatpak` em `editor/build.py` invocada no alvo Linux pela ação `dist`, gerando o pacote em `editor/dist/` e mantendo 100% de cobertura

## 3. Reestruturação do Manifesto Flatpak Oficial

- [x] 3.1 Atualizar `editor/flatpak/com.arestaclimb.Editor.yaml` adotando `base: io.qt.PySide.BaseApp` e runtime `org.kde.Platform` versão `6.8`
- [x] 3.2 Substituir a cópia do diretório PyInstaller no manifesto por instalação da árvore Python do editor e criação do script executável `/app/bin/EditorAresta` que invoca `python3 -m editor.main "$@"`

## 4. Pipeline de CI/CD e Exportação de Dependências

- [x] 4.1 Atualizar o workflow `.github/workflows/build_editor_linux.yml` para remover as etapas de `uv run editor/build.py dist` com PyInstaller e empacotamento do arquivo `.tar.gz`
- [x] 4.2 Adicionar ao workflow a exportação de dependências do grupo `editor` (via `uv export` e `flatpak-pip-generator`) e sincronização direta do `pypi-dependencies.json` no repositório `aresta-editor-flathub`

## 5. Validação e Testes Integrados

- [x] 5.1 Executar a suíte de testes completa do repositório (`editor/build_test.py`, `tests/fronteiras_plataforma_test.py`, `editor/core/configuracao_canal_test.py`) garantindo 100% de aprovação
- [x] 5.2 Validar a consistência do manifesto Flatpak e instruções de build para execução na VM de desenvolvimento
