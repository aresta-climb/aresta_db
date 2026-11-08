# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente, tanto `DialogoAdicionarMapa` (`editor/views/dialogos/dialogo_adicionar_mapa.py`) quanto `DialogoInserirImagemMarkdown` (`editor/views/dialogos/dialogo_inserir_imagem_markdown.py`) chamam `self._carregar_imagens_existentes()` sincronamente dentro de `__init__`. Em um croqui real com dezenas ou centenas de imagens WebP de alta resolução (1 MP a 2.5 MP), o construtor:
1. Lê os bytes completos de todos os arquivos da pasta `imagens/` no disco;
2. Decodifica cada imagem inteira em resolução máxima via `QPixmap.loadFromData`;
3. Cria `QIcon(pixmap)` sem reduzir para `96x96` px;
4. Em `DialogoAdicionarMapa`, copia os `bytes` brutos completos para o `UserRole` de cada `QListWidgetItem`.

Isso congela a thread principal do Qt por vários segundos antes mesmo de a janela aparecer na Aba 0 (`"Importar Nova Imagem"`).

## Goals / Non-Goals

**Goals:**
- Garantir abertura instantânea (`< 5 ms`) de `DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown` na Aba 0 (`"Importar Nova Imagem"`), sem I/O de disco nem decodificação de imagens da galeria no `__init__`.
- Carregar a galeria (`"Imagens do Croqui"`) de forma *lazy* ao alternar para a Aba 1 (ou sob demanda quando `_carregar_imagens_existentes()` for invocado explicitamente).
- Evitar leitura e armazenamento em massa de `bytes` brutos em cada `QListWidgetItem`: armazenar apenas o nome do arquivo no item e ler os bytes completos e metadados exclusivamente do item selecionado pelo usuário (`_ao_selecionar_item_galeria`).
- Criar e reutilizar um cache compartilhado de miniaturas `96x96` (`QIcon`) em memória nos componentes de diálogo de imagem (`editor/views/dialogos/componentes_dialogo_imagem.py`), indexado pelo caminho/estado de modificação (`mtime_ns` e tamanho no disco, ou `hash`/`id` dos bytes em RAM).

**Non-Goals:**
- Criar bancos de cache persistentes em disco (`.thumbs/`) ou threads complexas em segundo plano que dificultem o determinismo dos testes em `pytest-qt`.

## Decisions

### 1. Carregamento *Lazy* da Aba `"Imagens do Croqui"`
- **Decisão**: Remover `self._carregar_imagens_existentes()` do `__init__` de `DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`, mantendo uma flag `self._galeria_carregada: bool = False`. Quando o usuário (ou um teste) alternar para a Aba 1 (`_ao_trocar_aba(1)`), se `not self._galeria_carregada`, o diálogo chama `self._carregar_imagens_existentes()` e marca `self._galeria_carregada = True`.
- **Racional**: Na maioria das vezes em que o usuário clica em `"Substituir Imagem..."`, `"Trocar Imagem..."` ou `"Adicionar Mapa"`, ele permanece na Aba 0 (`"Importar Nova Imagem"`). Mesmo quando vai à Aba 1, a janela já está visível e responsiva. Além disso, como `tab_widget.setCurrentIndex(1)` dispara `currentChanged(1)` -> `_ao_trocar_aba(1)`, todos os fluxos de usuário e testes existentes que mudam para a Aba 1 continuam funcionando de forma transparente.

### 2. Cache Compartilhado de Miniaturas `96x96` em `componentes_dialogo_imagem.py`
- **Decisão**: Adicionar em `editor/views/dialogos/componentes_dialogo_imagem.py` a função `obter_icone_miniatura_imagem(nome_arquivo: str, pasta_imagens: Path | None, model: Any | None, tamanho: int = 96) -> QIcon | None` (com função auxiliar `limpar_cache_miniaturas_imagem()`).
  - Se a imagem estiver em memória RAM (`model.obter_bytes_imagem(f"imagens/{nome_arquivo}")` presente em `_imagens_em_memoria`), a chave de cache utiliza `("ram", nome_arquivo, len(bytes_ram), hash(bytes_ram[:256]), hash(bytes_ram[-256:]))`.
  - Se a imagem vier do disco (`pasta_imagens / nome_arquivo`), faz apenas `stat()` para obter `( str(caminho_abs), stat.st_mtime_ns, stat.st_size )`. Se a chave já estiver no cache `_CACHE_MINIATURAS`, retorna o `QIcon` `96x96` imediatamente **sem ler nem decodificar o arquivo do disco**!
  - Quando não estiver no cache, decodifica e redimensiona imediatamente para `96x96` (`pixmap.scaled(tamanho, tamanho, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)`), descartando o `QPixmap` de alta resolução e guardando apenas a miniatura `96x96` no cache.
- **Racional**: Reduz drasticamente o consumo de RAM (uma miniatura `96x96` ocupa ~36 KB contra ~10 MB de um `QPixmap` de 2.5 MP) e faz com que a segunda abertura da aba `"Imagens do Croqui"` leve menos de `2 ms` para centenas de imagens.

### 3. Leitura Sob Demanda dos Bytes Completos Apenas na Seleção
- **Decisão**: Em `DialogoAdicionarMapa._carregar_imagens_existentes()`, cada `QListWidgetItem` armazena apenas o `nome` do arquivo (`item.setData(Qt.ItemDataRole.UserRole, nome)`). Quando o usuário clica em um item (`_ao_selecionar_item_galeria`), o método lê os bytes reais daquele único arquivo via `_obter_bytes_imagem_croqui(nome)` (consultando `self.model.obter_bytes_imagem` ou `pasta_imagens / nome`) e calcula `obter_metadados_imagem(bytes_brutos)`.
- **Racional**: Elimina a cópia em memória de dezenas de megabytes de bytes WebP para itens da galeria que nunca serão clicados.

## Risks / Trade-offs

- **[Risco] Testes ou chamadores que inspecionam `dialogo.lista_imagens` sem trocar para a Aba 1** → **Mitigação**: Quando a intenção é usar a galeria, o fluxo público é `dialogo.tab_widget.setCurrentIndex(1)` (que aciona `_ao_trocar_aba(1)` e popula `lista_imagens`), e `_carregar_imagens_existentes()` continua disponível caso chamado diretamente.
- **[Risco] Imagem substituída em RAM continuar mostrando miniatura antiga na galeria** → **Mitigação**: A chave de cache verifica primeiro se a imagem está em `_imagens_em_memoria` (incluindo tamanho e amostra de hash dos bytes em RAM) ou `st_mtime_ns` do arquivo em disco, invalidando automaticamente qualquer miniatura cujo conteúdo tenha mudado.
