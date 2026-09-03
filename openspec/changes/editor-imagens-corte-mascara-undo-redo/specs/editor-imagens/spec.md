## MODIFIED Requirements

### Requirement: Integração do Editor de Imagens
O sistema SHALL fornecer um editor de imagens integrado para manipulação visual direta (corte por seleção, rotação e máscaras com conta-gotas), com todas as operações integradas à pilha global de histórico (`QUndoStack`) e sincronizadas via memória RAM com o `CroquiModel`.

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a uma imagem na árvore do Editor de Dados
- **THEN** o sistema SHALL exibir o widget de edição de imagens (`WidgetEditorImagens`) na parte direita da área central focando exclusivamente na edição daquela imagem selecionada.

#### Scenario: Listagem de Imagens
- **WHEN** o editor de imagens é carregado em modo autônomo ou via barra lateral "Imagens"
- **THEN** o sistema SHALL listar todas as imagens presentes na pasta `imagens/` do croqui atual e no buffer de memória RAM do modelo.

## ADDED Requirements

### Requirement: Rotação de Imagens com Histórico de Desfazer e Refazer
O sistema SHALL permitir rotacionar a imagem selecionada em passos de 90° (horário e anti-horário), gerando imediatamente um comando de substituição de imagem em memória RAM na pilha global de desfazer/refazer.

#### Scenario: Rotação Horária (+90°)
- **WHEN** o usuário aciona o botão de girar 90° no sentido horário
- **THEN** o sistema SHALL rotacionar a imagem em 90° à direita, comprimir a imagem resultante em WebP, registrar a alteração no `CroquiController` via `CmdSubstituirImagemMemoria` e atualizar imediatamente a cena do visualizador.

#### Scenario: Rotação Anti-horária (-90°)
- **WHEN** o usuário aciona o botão de girar 90° no sentido anti-horário
- **THEN** o sistema SHALL rotacionar a imagem em 90° à esquerda, comprimir a imagem resultante em WebP, registrar a alteração no `CroquiController` via `CmdSubstituirImagemMemoria` e atualizar imediatamente a cena do visualizador.

#### Scenario: Desfazer e Refazer Rotação
- **WHEN** o usuário executa uma rotação e posteriormente aciona Desfazer (`Ctrl+Z`) ou Refazer (`Ctrl+Y`)
- **THEN** o sistema SHALL restaurar a orientação original ou reaplicar a rotação de forma instantânea sem perdas.

### Requirement: Modo Cortar Interativo por Seleção de Área
O sistema SHALL fornecer um modo interativo de corte onde o usuário clica e arrasta sobre a imagem para demarcar a área desejada com *rubber band*, aplicando o corte imediatamente ao soltar o mouse e gravando a operação no histórico global de desfazer/refazer sem manter caixas de preview permanentes na cena.

#### Scenario: Ativação e Demarcação da Área de Corte
- **WHEN** o usuário clica no botão "Cortar"
- **THEN** o sistema SHALL ativar o modo de corte, alterar o cursor para mira (`CrossCursor`) e permitir desenhar um retângulo de seleção elástico ao clicar e arrastar sobre a imagem.

#### Scenario: Execução Imediata do Corte ao Soltar o Mouse
- **WHEN** o usuário solta o botão do mouse após demarcar uma área válida (superior a 10x10 pixels) no modo de corte
- **THEN** o sistema SHALL cortar a imagem nas coordenadas delimitadas, codificar a imagem resultante em WebP, despachar o comando para o `CroquiController`, atualizar a exibição e desativar o modo de corte.

#### Scenario: Cancelamento do Modo Cortar
- **WHEN** o usuário pressiona a tecla `Escape` ou clica novamente no botão "Cortar" antes de soltar uma seleção válida
- **THEN** o sistema SHALL cancelar a seleção, restaurar o cursor padrão e manter a imagem inalterada.

#### Scenario: Desfazer Corte via Histórico
- **WHEN** o usuário executa um corte e pressiona `Ctrl+Z`
- **THEN** o sistema SHALL restaurar imediatamente a imagem integral anterior ao corte.

### Requirement: Modo Máscara com Conta-gotas e Preenchimento Imediato
O sistema SHALL permitir cobrir trechos indesejados da imagem através da captura de cor com conta-gotas e desenho de retângulos que preenchem a área demarcada de forma atômica no histórico de desfazer/refazer.

#### Scenario: Captura de Cor e Preenchimento de Máscara
- **WHEN** o usuário ativa a ferramenta de máscara, clica em um pixel da imagem para capturar a cor e arrasta um retângulo sobre uma área de texto/artefato
- **THEN** o sistema SHALL pintar o retângulo com a cor capturada diretamente na imagem em RAM, registrar a ação como um comando na pilha de histórico e atualizar a visualização.

#### Scenario: Desfazer Máscara Aplicada
- **WHEN** o usuário aplica uma ou mais máscaras e aciona Desfazer (`Ctrl+Z`)
- **THEN** o sistema SHALL reverter a última máscara aplicada de forma atômica e independente.
