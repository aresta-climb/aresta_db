# Spec Delta

## ADDED Requirements

### Requirement: Cancelamento Seguro de Modos Interativos e Integridade do Ciclo de Vida da Cena
O `WidgetEditorMapas` SHALL cancelar e limpar proativamente todos os modos interativos temporários de desenho, medição e anotação (incluindo modo de polígono, traçado de novas rotas, modo de conversão de caixas, modo de linkagem e modo de câmera) sempre que a cena gráfica for descarregada, recarregada ou quando o mapa ativo for alternado. O sistema SHALL garantir a integridade dos itens temporários descartados em memória, impedindo tentativas de acesso ou mutação a objetos gráficos C++ previamente destruídos pelo Qt e prevenindo exceções de ciclo de vida (`libshiboken`).

#### Scenario: Troca de mapa durante desenho de polígono
- **WHEN** o usuário ativar o modo de desenho de polígono em um mapa e subsequentemente selecionar outro mapa na lista lateral
- **THEN** o `WidgetEditorMapas` SHALL cancelar imediatamente o modo de desenho ativo, desativando cursores e descartando itens temporários de cena com segurança
- **AND** novos cliques na área do novo mapa não SHALL tentar acessar itens da cena anterior nem lançar exceções de runtime do Shiboken

#### Scenario: Recarregamento de mapa com clear de cena
- **WHEN** a cena gráfica for recarregada ou limpa através de `carregar_mapa`, `descarregar_mapa` ou `_renderizar_mapa` enquanto um modo interativo (desenho de polígono ou nova rota) estiver em andamento
- **THEN** o sistema SHALL cancelar com segurança o modo interativo antes ou durante a limpeza da cena
- **AND** a rotina de remoção de itens temporários SHALL verificar se os objetos gráficos subjacentes ainda são válidos antes de solicitar sua remoção à cena

#### Scenario: Tentativa de clique com item temporário descartado
- **WHEN** ocorrer um evento de mouse (`mousePressEvent`, `mouseMoveEvent`) em um estado de desenho cujo item gráfico temporário tenha sido invalidado em C++
- **THEN** o sistema SHALL identificar a perda de validade do item gráfico (`shiboken6.isValid() == False` ou divergência de cena) e abortar a operação ou reiniciar o item sem propagar erro fatal de execução
