## ADDED Requirements

### Requirement: Captura de tela da janela ativa
O sistema DEVE permitir a captura visual instantânea do estado atual da janela do Editor Aresta no momento do acionamento do relato.

#### Scenario: Captura ao acionar relato na Janela Principal
- **WHEN** o usuário clica na ação de envio de relato na barra superior ou pressiona o atalho global `F12` (ou `Ctrl+Shift+F`)
- **THEN** o sistema captura o conteúdo gráfico da janela ativa em um `QPixmap` e abre o diálogo de relato com a imagem capturada carregada.

#### Scenario: Captura em telas iniciais do editor
- **WHEN** o usuário aciona o relato na `TelaDeAbertura` ou na `TelaDeCarregamento`
- **THEN** o sistema captura o estado visível da tela correspondente e exibe o diálogo de anotação.

### Requirement: Quadro de anotação e tarja de privacidade
O sistema DEVE disponibilizar um componente visual interativo (`WidgetQuadroAnotacao`) sobre a imagem capturada com ferramentas de caneta, destaque, tarja preta de privacidade e desfazer.

#### Scenario: Anotação com caneta livre e retângulo de destaque
- **WHEN** o usuário seleciona a ferramenta de Caneta ou Retângulo e desenha sobre a imagem
- **THEN** o quadro renderiza os traços e formas com a cor e espessura selecionadas, mantendo o histórico de traços para reversão (*desfazer*).

#### Scenario: Aplicação de tarja preta de privacidade
- **WHEN** o usuário seleciona a ferramenta de Tarja de Privacidade e arrasta uma área retangular sobre dados confidenciais (ex: fotos privadas ou caminhos de arquivos)
- **THEN** o quadro preenche a área selecionada com um retângulo preto sólido opaco, cobrindo e eliminando irreversivelmente os pixels subjacentes na imagem exportada.

#### Scenario: Desfazer anotações
- **WHEN** o usuário aciona a ação "Desfazer" no quadro
- **THEN** o último traço, forma ou tarja adicionada é removido da pilha de desenho.

### Requirement: Formulário de categorização e metadados
O sistema DEVE coletar a categoria do relato, comentário textual detalhado e metadados do usuário.

#### Scenario: Preenchimento do formulário
- **WHEN** o usuário abre o diálogo de relato
- **THEN** o sistema exibe opções de categoria ("Erro / Falha", "Sugestão / Melhoria", "Dúvida / Geral"), campo para descrição detalhada e pré-carrega o nome do autor configurado na sessão ativa.

### Requirement: Envio assíncrono e notificação ao usuário
O sistema DEVE despachar o relatório em segundo plano sem bloquear a interface gráfica e notificar o usuário do resultado.

#### Scenario: Envio de relato com sucesso
- **WHEN** o usuário clica em "Enviar Relato" com a descrição preenchida
- **THEN** o diálogo inicia uma tarefa assíncrona (`QThread`), exibe status de carregamento, envia o snapshot ao Sentry e Discord, fecha o diálogo ao concluir e exibe um `NotificacaoToast` de sucesso.

#### Scenario: Falha de conexão no envio
- **WHEN** ocorre erro de rede durante o despacho do relato
- **THEN** o diálogo exibe mensagem de alerta compreensível ao usuário e permite tentar novamente sem perder as anotações ou o texto digitado.
