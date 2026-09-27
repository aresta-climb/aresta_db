## 1. Padronização de Ícones e Estilos

- [x] 1.1 Validar e disponibilizar helper de ícone de lixeira discreto e estilos hover em `editor/views/estilo.py` e verificar com testes em `editor/views/estilo_test.py`
- [x] 1.2 Definir classes de estilo QSS para containers integrados de coleções repetidas e botões de rodapé em `editor/views/estilo.py`

## 2. Simplificação do Card de Mapas (`WidgetCardMapa`)

- [x] 2.1 Criar testes em `editor/views/componentes/widget_card_mapa_test.py` verificando a ausência de `btn_subir`/`btn_descer`, a presença exclusiva do botão discreto de lixeira à direita e o disparo da remoção
- [x] 2.2 Refatorar `WidgetCardMapa` em `editor/views/componentes/widget_card_mapa.py` para remover botões de setas e aplicar o botão de ícone discreto na extremidade direita do cabeçalho, verificando a aprovação dos testes

## 3. Container Integrado e Rodapé em `ContainerRepeatedWidget`

- [x] 3.1 Criar testes unitários em `editor/views/widget_editor_dados_test.py` para o posicionamento do botão `btn_add` no rodapé da coleção (após os itens) e ausência de botão no cabeçalho superior
- [x] 3.2 Refatorar `ContainerRepeatedWidget` em `editor/views/widget_editor_dados.py` para mover o botão de adição para o rodapé e exibir estado vazio amigável quando a lista contiver 0 itens
- [x] 3.3 Implementar container integrado emoldurado para campos primitivos escalares com campos `QLineEdit` horizontalmente responsivos e expansivos, sem larguras máximas artificiais
- [x] 3.4 Substituir o botão vermelho de remoção em cada linha de item escalar pelo botão de ícone de lixeira discreto e remover botões de setas soltos
- [x] 3.5 Implementar atalho de tecla `Enter` nos campos de texto escalares para criar automaticamente o próximo item no histórico e focar nele imediatamente, verificando via testes unitários

## 4. Harmonização de Mensagens Colapsáveis e Subelementos

- [x] 4.1 Atualizar `WidgetColapsavel` em `editor/views/widget_editor_dados.py` para exibir exclusivamente a alça de arraste na esquerda e a lixeira discreta na extrema direita do cabeçalho
- [x] 4.2 Atualizar `_renderizar_cartao_subelementos` em `editor/views/widget_editor_dados.py` para posicionar o botão de ação rápida de adição no corpo inferior do cartão em vez de comprimido à direita
- [x] 4.3 Atualizar os testes de `WidgetColapsavel` e cartões de subelementos em `editor/views/widget_editor_dados_test.py`

## 5. Validação Geral e Cobertura 100%

- [x] 5.1 Executar a suite completa de testes unitários do editor de dados (`pytest editor/views/widget_editor_dados_test.py editor/views/componentes/widget_card_mapa_test.py`) garantindo 100% de testes aprovados
- [x] 5.2 Executar validação do OpenSpec (`openspec validate redesign-campos-repeated --strict`) para certificar conformidade dos artefatos
