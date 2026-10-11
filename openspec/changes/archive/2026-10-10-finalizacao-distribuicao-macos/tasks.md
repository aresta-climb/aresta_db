# Tasks: Finalização da Distribuição macOS (Fase 1)

## 1. Configurações de Empacotamento e Metadados macOS

- [x] 1.1 Atualizar `editor/EditorAresta.spec` para incluir `keyring.backends.macOS` nos pacotes e imports ocultos no macOS e verificar consistência do spec
- [x] 1.2 Atualizar `editor/release_tools/empacotar_macos_dmg.py` para injetar `SUAutomaticallyUpdate` e `SUScheduledCheckInterval` no `Info.plist`, atualizando `editor/release_tools/empacotar_macos_dmg_test.py` com 100% de cobertura

## 2. Ponte de Integração Sparkle e Adaptador macOS

- [x] 2.1 Implementar módulo `editor/plataforma/macos/sparkle.py` com sua suíte de testes `editor/plataforma/macos/sparkle_test.py` para acionamento seguro do Sparkle via runtime Cocoa/ctypes com 100% de cobertura
- [x] 2.2 Atualizar `AdaptadorMacOS` em `editor/plataforma/macos/integracao.py` para checar `appcast.xml` com fallback resiliente, reportar `ATUALIZACAO_OBRIGATORIA` e acionar o Sparkle, cobrindo todos os cenários em `editor/plataforma/macos/integracao_test.py` com 100% de cobertura

## 3. Neutralização da Tela de Abertura e Validação de Integração

- [x] 3.1 Neutralizar a mensagem de atualização em `editor/views/tela_de_abertura.py` para não mencionar com exclusividade a Microsoft Store, atualizando testes em `editor/views/tela_de_abertura_test.py` e `editor/main_test.py`
- [x] 3.2 Executar a suíte de testes unitários e fronteiras de plataforma via `uv run pytest` e validar 100% de aprovação e conformidade

