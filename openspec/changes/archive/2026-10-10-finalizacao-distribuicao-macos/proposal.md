# Proposta: Finalização da Distribuição macOS (Fase 1)

## Por que

O Editor Aresta necessita de distribuição oficial para macOS (ARM64 / Apple Silicon) com imagem de disco DMG notarizada pela Apple e ciclo de atualização transparente in-app via Sparkle Framework. É fundamental garantir que usuários de Mac recebam atualizações obrigatórias e que o cofre de credenciais funcione confiavelmente em binários empacotados pelo PyInstaller sem conflito com o Keychain nativo.

## O que muda

- **Integração em Runtime com o Sparkle 2 no macOS**: O `AdaptadorMacOS` passa a consultar o feed `appcast.xml` no Cloudflare R2 durante a inicialização, reportando `StatusAtualizacao.ATUALIZACAO_OBRIGATORIA` quando houver versão superior, e delegando o download, diálogo de instalação e reinicialização ao Sparkle Framework nativo (`SPUStandardUpdaterController`).
- **Configuração de Atualização Obrigatória (Critical Updates)**: Adiciona suporte completo no `Info.plist` do bundle `.app` para download automático em segundo plano (`SUAutomaticallyUpdate = true`) e verificação automática com o Sparkle, sincronizado com a tag `<sparkle:criticalUpdate />` já emitida pelo gerador de feed.
- **Empacotamento do Keychain macOS no PyInstaller**: Garante que o arquivo de especificação do PyInstaller (`editor/EditorAresta.spec`) colete explicitamente `keyring.backends.macOS` e suas dependências de segurança em plataformas macOS, assegurando operação do cofre de credenciais em modo `onedir`.
- **Neutralização de Plataforma na Tela de Abertura**: Torna a mensagem de atualização na `TelaDeAbertura` agnóstica à loja (removendo menção exclusiva à "Microsoft Store"), suportando fluentemente macOS (Sparkle) e Linux.

## Capacidades

### Novas Capacidades
<!-- Nenhuma nova capacidade introduzida nesta mudança -->

### Capacidades Modificadas
- `editor-distribuicao-macos`: Requisitos de verificação de atualizações obrigatórias, acionamento do Sparkle 2 via `AdaptadorMacOS` e inclusão do backend de Keychain no empacotamento.

## Impacto

- **Código Afetado**:
  - `editor/plataforma/macos/integracao.py` e seu teste unitário `editor/plataforma/macos/integracao_test.py`.
  - `editor/EditorAresta.spec` para hidden imports do macOS.
  - `editor/release_tools/empacotar_macos_dmg.py` para chaves adicionais do Sparkle no `Info.plist`.
  - `editor/views/tela_de_abertura.py` e seu teste `editor/views/tela_de_abertura_test.py`.
- **Dependências**: Nenhuma dependência externa nova em Python (utiliza módulos nativos de `ctypes` / `urllib.request` / `xml.etree.ElementTree` com fallback defensivo gracioso fora do macOS).
