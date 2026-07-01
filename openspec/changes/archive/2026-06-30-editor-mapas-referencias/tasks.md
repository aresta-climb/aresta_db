## 1. MapasController e Comandos Protobuf

- [x] 1.1 Adicionar métodos no `MapasController` para despachar `CmdAdicionarRepeated` para adicionar novas referências (`campo_nome="referencias"`).
- [x] 1.2 Adicionar métodos no `MapasController` para despachar `CmdAlterarRepeatedItem` para modificar referências (atualizar lista de IDs ou ajuste_de_camera).
- [x] 1.3 Adicionar métodos no `MapasController` para despachar `CmdRemoverRepeated` para exclusão de referências.

## 2. Busca Global no CroquiModel

- [x] 2.1 Criar modal de busca / seletor iterando sobre `Pico -> Grupos -> Setores -> Escaladas` no `CroquiModel` carregado.
- [x] 2.2 Ao confirmar no modal, instanciar nova Referência protobuf preenchida com os campos (id de grupo, setor ou escalada correspondente) e disparar no Controller.

## 3. Componentes Visuais (Painel Direito)

- [ ] 3.1 Refatorar layout de `WidgetEditorMapas` para comportar um layout de 3 colunas (Adicionando QDockWidget ou layout normal para as Referências na direita).
- [ ] 3.2 Criar widget `PainelReferencias` que exibe cada Referência ativa em cards, escutando atualizações do Model para se redesenhar de acordo com `msg_mapa_proxy.referencias`.
- [ ] 3.3 Adicionar hover-events no painel direito que emitam um sinal temporário para a view central destacar as formas de `ids` no mapa.

## 4. View Central: Modo Linkagem (Pointer/Click)

- [x] 4.1 Adicionar "Modo Linkagem" à View Central (ex: Enum de estado e cursor de crosshair ou link).
- [x] 4.2 Alterar tratativa de cliques na cena gráfica: se em "Modo Linkagem", o clique na Box/Círculo identifica o POI clicado e invoca método no `MapasController` para adicionar/remover aquele `id` à referência ativa selecionada no momento.

## 5. Overlay Visual e Ajuste de Câmera (WYSIWYG)

- [x] 5.1 Criar overlay interativo (Caixa arrastável/redimensionável com proporção 9:16) no `GraphicsScene` da view central.
- [x] 5.2 Adicionar estilo visual que escureça os 20% do topo e base do overlay (simulando corte de cabeçalho do app).
- [x] 5.3 Criar botão "Salvar Ajuste Câmera" na UI do Card da Referência, que extrai as dimensões e centro dessa caixa, calcula os offsets (`posicao_vertical`, `posicao_horizontal`, `zoom`) e altera a Referência via Controller.
- [x] 5.4 Testar e calibrar as contas matemáticas da caixa WYSIWYG x Protobuf camera offset para refletirem a experiência móvel correta.
