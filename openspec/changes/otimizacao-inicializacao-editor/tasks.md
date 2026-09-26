## 1. Otimização da Telemetria Sentry

- [ ] 1.1 Atualizar `editor/core/telemetria_test.py` para testar a desativação de integrações automáticas (`auto_enabling_integrations=False`) e verificar que os testes falham inicialmente (TDD Vermelho)
- [ ] 1.2 Implementar `auto_enabling_integrations=False` na chamada `sentry_sdk.init` em `editor/core/telemetria.py` e verificar aprovação com 100% de cobertura via `pytest editor/core/telemetria_test.py --cov=editor.core.telemetria` (TDD Verde)

## 2. Arranque Rápido e Imports Sob Demanda no Ponto de Entrada

- [ ] 2.1 Atualizar testes unitários em `editor/main_test.py` cobrindo a instanciação imediata do `QApplication` e o carregamento sob demanda para os modos local e padrão (TDD Vermelho)
- [ ] 2.2 Reorganizar `editor/main.py` removendo imports globais pesados e carregando dependências sob demanda no interior das ramificações de execução, verificando aprovação com 100% de cobertura via `pytest editor/main_test.py --cov=editor.main` (TDD Verde)

## 3. Carregamento Sob Demanda na Janela Principal

- [ ] 3.1 Atualizar testes unitários em `editor/legacy_views/area_principal_test.py` cobrindo a instanciação sob demanda de `WidgetEditorMapas` na mudança de aba e supressão de instanciação em abas ocultas (TDD Vermelho)
- [ ] 3.2 Modificar `editor/legacy_views/area_principal.py` para postergar a criação do `WidgetEditorMapas` até a ativação da aba de mapas e evitar instanciação do `PainelCuradoria` enquanto a aba estiver oculta, verificando com `pytest editor/legacy_views/area_principal_test.py` (TDD Verde)

## 4. Empacotamento PyInstaller onedir e Integração MSIX

- [ ] 4.1 Atualizar `editor/build_test.py` para incluir asserções do modo de compilação em diretório (`onedir`), desativação de UPX e verificação do diretório de destino `editor/dist/EditorAresta/` (TDD Vermelho)
- [ ] 4.2 Alterar `editor/EditorAresta.spec` e `editor/build.py` para gerar a distribuição em diretório utilizando `COLLECT` com `upx=False`, verificando aprovação com 100% de cobertura via `pytest editor/build_test.py --cov=editor.build` (TDD Verde)
- [ ] 4.3 Atualizar `.github/workflows/release-editor.yml` para copiar o conteúdo completo de `editor/dist/EditorAresta/` para a pasta de staging do pacote MSIX e verificar a sintaxe do workflow

## 5. Validação e Integração Ponta a Ponta

- [ ] 5.1 Executar a suíte de testes completa do editor (`pytest editor/`) garantindo conformidade com o princípio de 100% de cobertura de testes unitários nas bibliotecas alteradas
- [ ] 5.2 Executar a inicialização em modo local e modo padrão via linha de comando, medindo o tempo de aparecimento da primeira interface gráfica para confirmar que é inferior a 1 segundo
