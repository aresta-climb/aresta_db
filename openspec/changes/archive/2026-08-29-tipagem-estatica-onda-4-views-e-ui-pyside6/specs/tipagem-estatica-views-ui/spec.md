# Especificação: Tipagem Estática em Views e UI PySide6

## ADDED Requirements

### Requirement: Tipagem Estática Estrita em Modelos Remanescentes
Os módulos `editor/models/croqui_model.py` e `editor/models/compilacao_log.py` SHALL possuir tipagem estática estrita em todos os métodos, propriedades e sinais Qt.

#### Scenario: Validação de modelos pelo MyPy
- **WHEN** o MyPy analisa `editor/models/croqui_model.py` e `editor/models/compilacao_log.py`
- **THEN** nenhuma inconsistência de tipo ou chamada não tipada é reportada sob modo estrito.

### Requirement: Tipagem Estática Estrita em Views Principais e Estilos
Os módulos `editor/views/estilo.py`, `editor/views/notificacao.py`, `editor/views/publish_dialog.py`, `editor/views/tela_de_abertura.py` e `editor/views/dialogo_recuperacao_sessao.py` SHALL possuir anotações de tipo completas em suas funções utilitárias e classes de diálogo.

#### Scenario: Validação de views e estilos pelo MyPy
- **WHEN** o MyPy analisa esses módulos de visualização
- **THEN** todas as funções e métodos são aprovados com 0 erros.

### Requirement: Tipagem Estática Estrita em Widgets de Edição e Árvores
Os componentes `tree_view_adapter.py`, `protobuf_widget_factory.py`, `widget_campo_coordenada_e7.py`, `widget_campo_imagem.py`, `widget_editor_dados.py`, `widget_editor_mapas.py`, `widget_mensagem_coordenada.py`, `widget_painel_referencias.py` e `widget_saida_compilacao.py` SHALL possuir anotações completas de widgets, eventos e layouts.

#### Scenario: Validação de widgets pelo MyPy
- **WHEN** o MyPy analisa a árvore de widgets em `editor/views/`
- **THEN** nenhuma violação de tipo é encontrada em modo estrito.

### Requirement: Tipagem Estática Estrita em Diálogos Especializados
Todos os diálogos em `editor/views/dialogos/` SHALL possuir tipos estritos em construtores, formulários e retornos de dados.

#### Scenario: Validação de diálogos de formulário pelo MyPy
- **WHEN** o MyPy analisa os módulos em `editor/views/dialogos/`
- **THEN** todas as classes de diálogo são validadas com sucesso.

### Requirement: Tipagem Estática Estrita em Views Legadas e Entrada Principal
Os módulos em `editor/legacy_views/` e o arquivo `editor/main.py` SHALL possuir anotações completas de tipo compatíveis com MyPy estrito.

#### Scenario: Validação de views legadas e main.py
- **WHEN** o MyPy analisa `editor/legacy_views/` e `editor/main.py`
- **THEN** a verificação conclui com código de saída 0.

### Requirement: Conformidade no Teste Guardião da Onda 4
O teste `tests/tipagem_estatica_test.py` SHALL incluir todos os módulos da Onda 4 na lista de verificação de tipos e conformidade AST.

#### Scenario: Execução dos testes automatizados de tipagem
- **WHEN** o pytest executa `tests/tipagem_estatica_test.py`
- **THEN** todos os testes passam garantindo 100% de cobertura de tipos na camada visual.
