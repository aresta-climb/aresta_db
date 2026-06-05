## 1. Refatoração de Arquivos e Nomenclatura

- [x] 1.1 Criar `editor/views/tela_de_carregamento.py` a partir do conteúdo de `pagina_inicial.py`
- [x] 1.2 Criar `editor/views/tela_de_carregamento_test.py` a partir do conteúdo de `pagina_inicial_test.py`
- [x] 1.3 Remover `editor/views/pagina_inicial.py` e `editor/views/pagina_inicial_test.py`
- [x] 1.4 Atualizar imports e nome da classe em `tela_de_carregamento.py` e seu teste

## 2. Implementação da Nova Interface (QDialog)

- [x] 2.1 Refatorar `TelaDeCarregamento` para herdar de `QDialog`
- [x] 2.2 Restaurar nomes completos dos botões: "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial"
- [x] 2.3 Remover efeitos de sombra internos (não necessários em janelas nativas) e ajustar dimensões
- [x] 2.4 Implementar lógica para exibir "Nenhum croqui no histórico" quando a lista estiver vazia

## 3. Integração e Validação

- [x] 3.1 Atualizar `editor/main.py` para exibir a `TelaDeCarregamento` como um diálogo antes da `JanelaPrincipal`
- [x] 3.2 Atualizar testes unitários em `tela_de_carregamento_test.py`
- [x] 3.3 Validar visualmente o diálogo e o fluxo de transição
