## Why

No editor de mapas, elementos de traçado vetorial (ItemTrajetoLinha) herdam de QGraphicsPathItem sem sobrescrever shape(). A implementação padrão do Qt adiciona o interior do caminho ao formato de colisão (p.addPath(path)), o que faz com que curvas abertas (especialmente travessias e rotas que contornam blocos) sejam tratadas como polígonos fechados gigantes. Isso faz com que qualquer clique no espaço vazio entre os extremos da curva selecione inadvertidamente o traçado errado, bloqueando a seleção precisa de nós e vias vizinhas. Além disso, ao selecionar uma curva, o Qt desenha uma caixa delimitadora retangular tracejada (oundingRect) que polui a visualização do croqui e induz à falsa percepção de que a seleção é puramente retangular.

## What Changes

- **Hit-Testing Estrito em Traçados Vetoriais**: Sobrescrever shape() em ItemTrajetoLinha utilizando QPainterPathStroker com largura de tolerância de clique (ex: 12px a 14px), sem incluir o interior preenchido (path), garantindo que apenas cliques diretamente sobre o traçado (ou em sua vizinhança imediata) disparem a seleção da linha.
- **Destaque Visual Orgânico na Seleção**: Substituir a caixa delimitadora retangular tracejada padrão do Qt (QStyle::State_Selected em paint()) por uma renderização de seleção dedicada, desenhando um halo/contorno de destaque de alto contraste diretamente ao longo do spline da curva.
- **Preservação da Interação de Nós**: Garantir que as alças de nós (AlcaNoTrajeto) continuem recebendo eventos prioritários de clique e arrasto sem interferência de polígonos fantasmas da linha pai ou de linhas vizinhas.

## Capabilities

### Modified Capabilities
- 	racados-vetoriais-mapas: Adiciona os requisitos de hit testing estrito baseado em traçado (stroke) e de renderização de destaque visual da curva selecionada sem caixa delimitadora retangular.

## Impact

- **Código Afetado**: ditor/views/widget_editor_mapas.py (ItemTrajetoLinha).
- **Testes**: ditor/views/widget_editor_mapas_test.py com cobertura de 100% para os novos métodos shape() e paint() de seleção.
- **APIs / Dados**: Nenhuma alteração no modelo de dados Protobuf ou nos arquivos croqui.yaml; a mudança é estritamente no subsistema visual e de interação do editor.
