## 1. Testes Automatizados de Hit-Testing e Seleção (TDD Red)

- [x] 1.1 Criar testes unitários em ditor/views/widget_editor_mapas_test.py verificando que ItemTrajetoLinha.shape() restringe colisões ao stroke (não detecta ponto no vão de curva côncava, mas detecta pontos sobre a linha dentro da tolerância)
- [x] 1.2 Criar testes unitários em ditor/views/widget_editor_mapas_test.py verificando que ItemTrajetoLinha.paint() em estado selecionado suprime a caixa pontilhada retangular padrão do Qt e desenha o halo de seleção sobre o path

## 2. Implementação da Geometria e Renderização (TDD Green)

- [x] 2.1 Implementar o método shape() em ItemTrajetoLinha (ditor/views/widget_editor_mapas.py) utilizando QPainterPathStroker com tolerância ergonômica e verificar aprovação dos testes de colisão
- [x] 2.2 Atualizar o método paint() em ItemTrajetoLinha (ditor/views/widget_editor_mapas.py) para limpar State_Selected antes de chamar o super().paint() e desenhar o halo luminoso de destaque ao longo do traçado

## 3. Verificação de Integração e Cobertura 100%

- [x] 3.1 Executar a suíte de testes do editor de mapas (pytest editor/views/widget_editor_mapas_test.py) e validar 100% de cobertura nos métodos modificados
- [x] 3.2 Validar a interação entre AlcaNoTrajeto e ItemTrajetoLinha garantindo que cliques sobre nós de vias vizinhas não sofrem interferência da curva
