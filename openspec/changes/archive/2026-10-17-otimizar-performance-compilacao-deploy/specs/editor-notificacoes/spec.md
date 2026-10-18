# Spec Delta

## ADDED Requirements

### Requirement: Posicionamento do Indicador de Salvamento em Andamento no Canto Inferior Direito
Durante o processo de salvamento assíncrono na janela principal do editor (`AreaPrincipal`), o sistema SHALL posicionar o indicador visual `"Salvando..."` no canto inferior direito da janela (com margem de 20px das bordas direita e inferior), alinhado na mesma região espacial onde a notificação temporária (`NotificacaoToast`) de conclusão do salvamento é exibida.

#### Scenario: Exibição e reposicionamento do indicador "Salvando..." no canto inferior direito
- **WHEN** o usuário inicia o salvamento do croqui na `AreaPrincipal`
- **THEN** o indicador `"Salvando..."` SHALL ser exibido no canto inferior direito da janela principal e, ao concluir o salvamento, SHALL ser ocultado dando lugar ao `NotificacaoToast` no mesmo canto inferior direito.
