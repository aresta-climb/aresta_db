# Tasks

## 1. Cache Compartilhado de Miniaturas `96x96` (`editor/views/dialogos/componentes_dialogo_imagem.py`)

- [x] 1.1 Escrever testes comportamentais (Red) em `editor/views/dialogos/componentes_dialogo_imagem_test.py` para `obter_icone_miniatura_imagem` e `limpar_cache_miniaturas_imagem`, cobrindo geração de ícone `96x96`, hit de cache sem releitura de disco, invalidação por modificação de arquivo ou por substituição de bytes em RAM e tratamento de arquivo corrompido/ausente
- [x] 1.2 Implementar `obter_icone_miniatura_imagem` e `limpar_cache_miniaturas_imagem` em `editor/views/dialogos/componentes_dialogo_imagem.py` e verificar 100% de cobertura em `uv run pytest editor/views/dialogos/componentes_dialogo_imagem_test.py --cov=editor.views.dialogos.componentes_dialogo_imagem --cov-report=term-missing -o addopts=""`

## 2. Carregamento *Lazy* e Leitura Sob Demanda nos Diálogos (`DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`)

- [x] 2.1 Escrever testes comportamentais (Red) em `editor/views/dialogos/dialogo_adicionar_mapa_test.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py` verificando que a instanciação na Aba 0 (`"Importar Nova Imagem"`) não popula `lista_imagens` nem decodifica a galeria até a alternância para a Aba 1 (`"Imagens do Croqui"`), e que a seleção carrega os bytes completos sob demanda
- [x] 2.2 Atualizar `editor/views/dialogos/dialogo_adicionar_mapa.py` e `editor/views/dialogos/dialogo_inserir_imagem_markdown.py` para carregar a galeria de forma *lazy* ao abrir a Aba 1, reutilizar `obter_icone_miniatura_imagem` e ler os bytes completos apenas do item selecionado, verificando 100% de cobertura com `uv run pytest editor/views/dialogos/dialogo_adicionar_mapa_test.py editor/views/dialogos/dialogo_inserir_imagem_markdown_test.py --cov=editor.views.dialogos.dialogo_adicionar_mapa --cov=editor.views.dialogos.dialogo_inserir_imagem_markdown --cov-report=term-missing -o addopts=""`
