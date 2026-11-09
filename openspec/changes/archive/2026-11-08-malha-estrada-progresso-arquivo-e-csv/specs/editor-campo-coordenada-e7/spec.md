# Spec Delta

## MODIFIED Requirements

### Requirement: Geração e indicador de mapa de pontos de estrada na localização do Pico
Exclusivamente ao editar o campo `localizacao` de uma mensagem `Pico`, o componente `WidgetMensagemCoordenada` SHALL exibir um botão `Gerar Mapa de Pontos` e um indicador de status que alerta com warning quando a malha rodoviária não estiver gerada para a coordenada atual, executando a geração em background (`QThread`) com uma janela modal de progresso (`DialogoProgressoMalhaEstrada`) contendo barra de progresso, log das etapas em tempo real e botão `Cancelar`, e atualizando `pico.malha_estrada.conteudo` via comando do controlador ao concluir com sucesso.

#### Scenario: Exibição de warning quando o mapa de pontos não foi gerado ou está defasado
- **WHEN** o formulário renderiza `Pico.localizacao` com coordenadas válidas e `pico.malha_estrada.conteudo` está vazia ou possui coordenadas de referência diferentes da localização atual
- **THEN** o widget exibe o botão `Gerar Mapa de Pontos` e o aviso visual de que o mapa de pontos de estrada não foi gerado para aquela localização.

#### Scenario: Geração do mapa de pontos ao clicar no botão ou editar coordenada do Pico
- **WHEN** o usuário clica em `Gerar Mapa de Pontos` (ou confirma a edição/colagem de coordenadas válidas em `Pico.localizacao`) com acesso à Overpass API
- **THEN** o Editor abre a janela de progresso exibindo o percentual e o log de cada etapa em background sem congelar a UI e, ao concluir, grava `pico.malha_estrada.conteudo` via comando do controlador (suportando Undo/Redo) e atualiza o indicador para o estado gerado.

#### Scenario: Cancelamento pelo usuário durante a geração do mapa de pontos
- **WHEN** a janela de progresso está aberta e o usuário clica no botão `Cancelar`
- **THEN** o worker em background é interrompido, a janela de progresso é fechada sem alterar `pico.malha_estrada` e o Editor permanece responsivo.

#### Scenario: Falha de conexão ao tentar gerar o mapa de pontos no Editor
- **WHEN** a consulta à Overpass API falha por ausência de internet durante a geração em background
- **THEN** o Editor preserva a edição das coordenadas sem bloquear o usuário e mantém visível o warning e o botão `Gerar Mapa de Pontos` para nova tentativa.

#### Scenario: Omissão do botão e do warning em coordenadas que não pertencem a Pico
- **WHEN** `WidgetMensagemCoordenada` é instanciado para coordenadas de `Setor`, `Grupo` ou `PontoDeInteresse`
- **THEN** o botão `Gerar Mapa de Pontos` e o indicador de status da malha rodoviária não são exibidos.
