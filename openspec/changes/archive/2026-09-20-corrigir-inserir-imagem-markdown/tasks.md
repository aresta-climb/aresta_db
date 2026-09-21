## 1. Preservação de Imagens na Limpeza e Compilação

- [x] 1.1 Criar testes unitários em `tests/scripts/preparar_submissao_lib_test.py` demonstrando a preservação de imagens Markdown em `croqui.descricao`, `pico.descricao`, `escaladas` (`via_esportiva`, `via_movel`, `boulder`, etc.), `trilhas` e pontos de interesse, verificando que o teste falha antes da alteração (TDD).
- [x] 1.2 Implementar a coleta recursiva e universal de referências de imagens Markdown em `coletar_referencias_arquivos` no arquivo `scripts/preparar_submissao_lib.py` e verificar que todos os testes de submissão e limpeza passam com `pytest tests/scripts/preparar_submissao_lib_test.py`.

## 2. Componente Visual Reutilizável AreaDropImagem (Library-First)

- [x] 2.1 Criar testes unitários em `editor/views/componentes/area_drop_imagem_test.py` validando os eventos de drag enter, drop, clique para seleção de arquivo, emissão de sinal `imagem_selecionada` e renderização de preview.
- [x] 2.2 Implementar `AreaDropImagem` em `editor/views/componentes/area_drop_imagem.py`, refatorar `editor/views/dialogos/dialogo_adicionar_mapa.py` para utilizar o novo componente e verificar a passagem dos testes com `pytest tests/editor/views/dialogos/dialogo_adicionar_mapa_test.py editor/views/componentes/area_drop_imagem_test.py`.

## 3. Unificação Visual do Diálogo de Inserção de Imagem Markdown

- [x] 3.1 Atualizar testes unitários em `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py` cobrindo o cabeçalho com botão "Selecionar Imagem...", área de drop `AreaDropImagem`, painel de metadados ricos (dimensões e peso WebP vs original), campo de nome de destino com validação de colisão em tempo real e legenda obrigatória.
- [x] 3.2 Refatorar `DialogoInserirImagemMarkdown` em `editor/views/dialogos/dialogo_inserir_imagem_markdown.py` com a interface unificada alinhada a `DialogoAdicionarMapa` e validar que 100% dos testes unitários passam com `pytest editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py`.

## 4. Integração com o Histórico Transacional (Princípio VII)

- [x] 4.1 Criar teste unitário em `editor/views/widget_editor_dados_test.py` validando que ao inserir imagem em campo Markdown, o comando é empilhado na pilha `historico`, permitindo desfazer (`Ctrl+Z`) e refazer (`Ctrl+Y`) tanto o texto quanto o registro dos bytes da imagem no modelo.
- [x] 4.2 Implementar comando de histórico (`ComandoInserirImagemMarkdown`) e amarrá-lo ao `WidgetEditorMarkdown`, garantindo a integridade transacional e verificando que os testes passam com `pytest editor/views/widget_editor_dados_test.py`.

## 5. Validação de Integração e Regressão

- [x] 5.1 Executar a suíte completa de testes do editor e scripts para garantir 100% de unit test coverage e ausência de regressões (`pytest tests/`).
- [x] 5.2 Realizar verificação prática ponta a ponta: inserir imagem em markdown, salvar, simular reabertura do croqui e validar que o arquivo WebP permanece em `imagens/` e pronto para commit.
