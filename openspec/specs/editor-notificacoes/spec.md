# editor-notificacoes Specification

## Purpose
Define o comportamento visual, posicionamento e ciclo de vida das notificações temporárias (toasts) e indicadores de status de operações assíncronas (como salvamento) na interface gráfica do Aresta Editor.

## Requirements
### Requirement: Notificação Temporária (Toast)
O sistema SHALL permitir a exibição de notificações curtas e temporárias na interface do usuário para fornecer feedback sobre ações realizadas (ex: salvamento, exportação).

#### Scenario: Exibição de notificação de sucesso
- **WHEN** o sistema solicita a exibição de uma notificação de sucesso com o texto "Salvo com sucesso"
- **THEN** um pequeno widget SHALL aparecer no canto inferior direito da janela principal contendo o texto e um ícone de "check" verde.

### Requirement: Auto-ocultação de Notificações
As notificações SHALL desaparecer automaticamente após um período de tempo pré-determinado sem intervenção do usuário.

#### Scenario: Notificação desaparece após timeout
- **WHEN** uma notificação é exibida E o tempo de 3 segundos transcorre
- **THEN** a notificação SHALL desaparecer suavemente da tela (fade-out).

### Requirement: Posicionamento do Indicador de Salvamento em Andamento no Canto Inferior Direito
Durante o processo de salvamento assíncrono na janela principal do editor (`AreaPrincipal`), o sistema SHALL posicionar o indicador visual `"Salvando..."` no canto inferior direito da janela (com margem de 20px das bordas direita e inferior), alinhado na mesma região espacial onde a notificação temporária (`NotificacaoToast`) de conclusão do salvamento é exibida.

#### Scenario: Exibição e reposicionamento do indicador "Salvando..." no canto inferior direito
- **WHEN** o usuário inicia o salvamento do croqui na `AreaPrincipal`
- **THEN** o indicador `"Salvando..."` SHALL ser exibido no canto inferior direito da janela principal e, ao concluir o salvamento, SHALL ser ocultado dando lugar ao `NotificacaoToast` no mesmo canto inferior direito.
