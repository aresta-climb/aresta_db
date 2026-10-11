# Design Técnico: Finalização da Distribuição macOS (Fase 1)

## Contexto

Consulte `proposal.md` para a motivação. Atualmente, o `AdaptadorMacOS` possui métodos stub para atualizações (`verificar_atualizacoes_disponiveis` retorna estaticamente `SEM_ATUALIZACAO`). As ferramentas de release (`empacotar_macos_dmg.py` e `gerador_feed_sparkle.py`) já montam o bundle `EditorAresta.app`, assinam com *Developer ID*, realizam notarização Apple com `notarytool`, copiam o `Sparkle.framework` para `Contents/Frameworks/` e geram o `appcast.xml` assinado com Ed25519 e marcado com `<sparkle:criticalUpdate />`.

Falta conectar a verificação e o acionamento em tempo de execução dentro do editor, garantir o empacotamento completo do Keychain no PyInstaller e neutralizar o texto de atualização da `TelaDeAbertura`.

## Metas e Não-Metas

**Metas:**
- Integrar a detecção de atualizações obrigatórias no `AdaptadorMacOS` comparando a versão local com o `appcast.xml` do Cloudflare R2.
- Acionar o diálogo nativo do Sparkle Framework através de despacho seguro ao runtime Cocoa/Objective-C (`SPUStandardUpdaterController`).
- Garantir que `keyring.backends.macOS` seja explicitamente incluído no PyInstaller em builds para macOS.
- Manter 100% de cobertura de testes unitários com testes de fronteira e isolamento multiplataforma em runners Linux/Windows.

**Não-Metas:**
- Submissão à Mac App Store (Fase 2, que exigirá App Sandbox estrito e exclusão do Sparkle).
- Suporte a binários legados Intel x86_64 (foco exclusivo em Apple Silicon ARM64, conforme especificação).
- Reimplementação da interface de download do Sparkle em Qt/QML (o Sparkle cuida de toda a UX nativa de progresso, permissões de escrita em `/Applications` e reinício seguro).

## Decisões Técnicas

### 1. Detecção Leve no Arranque via Consulta ao Feed RSS
- **Escolha**: O `AdaptadorMacOS.verificar_atualizacoes_disponiveis()` faz uma requisição HTTP simples (via `urllib.request`) com timeout estrito de 2 segundos para `https://serving.arestaclimb.com/editor-macos/appcast.xml`. Extrai a versão da tag `<enclosure sparkle:version="...">` e verifica a presença da tag `<sparkle:criticalUpdate />`.
- **Alternativas consideradas**:
  - *Delegar 100% ao timer interno do Sparkle sem consultar na inicialização*: Deixaria o editor abrir com a versão desatualizada até que o timer assíncrono do Sparkle disparasse a janela, permitindo que o usuário realizasse operações com esquemas antigos.
  - *Usar biblioteca pesada de terceiros para parsing*: Desnecessário; `xml.etree.ElementTree` é embutido na biblioteca padrão do Python e atende perfeitamente ao formato RSS 2.0.

### 2. Acionamento do Sparkle via Cocoa Runtime com Fallback Defensivo
- **Escolha**: Criar um módulo auxiliar `editor/plataforma/macos/sparkle.py` que localiza o `Sparkle.framework` dentro de `Contents/Frameworks/` ou via `@rpath`. Utiliza `ctypes` para invocar `SPUStandardUpdaterController` (método `checkForUpdates:`). Caso o framework não esteja carregado ou execute em ambiente sem Cocoa (como testes em Linux/Windows), opera em modo fallback seguro e sem exceções.
- **Alternativas consideradas**:
  - *Adicionar `pyobjc` como dependência obrigatória do projeto*: Rejeitado para evitar sobrecarga de dependências de dezenas de megabytes na suíte multiplataforma do repositório. `ctypes` é nativo do Python e suficiente para chamar os métodos de despacho do Objective-C.

### 3. Configuração do `Info.plist` para Atualizações em Segundo Plano
- **Escolha**: Adicionar as chaves `SUAutomaticallyUpdate = true` e `SUScheduledCheckInterval = 3600` em `editor/release_tools/empacotar_macos_dmg.py`.
- **Justificativa**: Garante que o Sparkle baixe o delta/DMG em segundo plano quando disponível, tornando o diálogo de reinicialização imediato e sem espera de download.

### 4. Coleta Explícita do Keychain no `EditorAresta.spec`
- **Escolha**: Adicionar `keyring.backends.macOS` e submódulos necessários à lista de `hiddenimports` e `pacotes_para_coletar` no PyInstaller quando `sys.platform == "darwin"`.
- **Justificativa**: Evita erros de `NoKeyringError` quando o aplicativo roda empacotado fora do ambiente de desenvolvimento.

### 5. Neutralização da Mensagem de Atualização na `TelaDeAbertura`
- **Escolha**: Alterar o texto padrão da `label_update_info` em `editor/views/tela_de_abertura.py` para um formato agnóstico ("Uma nova versão do Editor Aresta ({versao}) está disponível. Por favor, atualize o aplicativo para continuar.").
- **Justificativa**: Não exibir menção à "Microsoft Store" quando o aplicativo estiver rodando no macOS ou no Linux.

## Riscos e Mitigações

- **[Conectividade instável ou offline no arranque]** → *Mitigação*: A consulta HTTP possui timeout de 2 segundos. Se falhar por conexão ou timeout, o `AdaptadorMacOS` retorna `StatusAtualizacao.SEM_ATUALIZACAO`, permitindo a inicialização do editor em modo offline local.
- **[Execução de testes em ambiente não-macOS]** → *Mitigação*: O carregamento do Sparkle e a consulta ao Keychain são totalmente desacoplados e testáveis com mocks e injeção de dependências em `integracao_test.py`, mantendo a suíte de testes 100% verde no Linux.
- **[Diferenças de permissão de escrita em `/Applications`]** → *Mitigação*: O Sparkle Framework 2 possui ferramenta auxiliar interna (`Autoupdate.app`) que eleva privilégios via Authorization Services da Apple de forma transparente.
