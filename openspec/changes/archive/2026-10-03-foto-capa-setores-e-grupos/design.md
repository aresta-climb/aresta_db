# Design Técnico: Foto de Capa para Setores e Grupos

## Contexto (Context)

Atualmente, `croqui.proto` possui `caminho_thumbnail` no nível raiz de `Croqui`, com `CampoFormatoUi.IMAGEM` e geração do widget [`WidgetCampoImagem`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_campo_imagem.py). No entanto, as mensagens `Setor` e `Grupo` não possuem campo de imagem de capa, armazenando fotos descritivas apenas no corpo livre de arquivos Markdown via tags `![alt](caminho)`.

Para detalhes de motivação, consulte [proposal.md](file:///c:/Renato/Devel/aresta-climb/aresta_db/openspec/changes/foto-capa-setores-e-grupos/proposal.md).

## Objetivos e Não-Objetivos (Goals / Non-Goals)

**Objetivos:**
- Adicionar o campo `caminho_imagem_capa` às mensagens `Setor` e `Grupo` no `croqui.proto`.
- Garantir que o campo de capa seja exibido no topo dos formulários de dados (`widget_editor_dados.py`) acima do campo `nome`.
- Configurar e garantir o limite de resolução estrita de 1 Megapixel (`AREA_MAXIMA_ESCALADA` = 1.000.000 px) para fotos de capa.
- Atualizar a biblioteca [`editor/core/imagens_croqui.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/imagens_croqui.py) para que capas sejam rastreadas no ciclo de vida de memória e detecção de imagens órfãs.
- Criar script utilitário idempotente [`scripts/extrair_capas_markdown.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/scripts/extrair_capas_markdown.py) com testes unitários para migração ampla das fotos existentes nos markdowns da base de dados.
- Assegurar 100% de cobertura de testes unitários e integração conforme Princípios Aresta.

**Não-Objetivos:**
- Criar script de migração numerado em `migracoes/` (a adição de campos opcionais não quebra compatibilidade com clientes legados).
- Adicionar campo de capa à entidade `Pico` (o Pico já é contemplado pela thumbnail do Croqui).
- Modificar o código do cliente Flutter móvel neste repositório (os protos Dart são gerados aqui e consumidos pelo app).

## Decisões Técnicas (Decisions)

### Decisão 1: Nomenclatura e Tipagem do Campo
- **Escolha:** `string caminho_imagem_capa = 5;` em `Setor` e `Grupo`.
- **Anotações Protobuf:**
  ```protobuf
  string caminho_imagem_capa = 5 [
    (aresta.tipo_conteudo) = CAMINHO,
    (aresta.mime_type) = "image/webp",
    (aresta.formato_na_ui) = IMAGEM,
    (aresta.texto_na_ui) = "Foto de Capa"
  ];
  ```
- **Alternativas consideradas:** `caminho_foto_capa` ou `foto_capa`. `caminho_imagem_capa` foi preferido por manter coerência direta com `caminho_imagem_mapa`.

### Decisão 2: Posicionamento Prioritário na UI
- **Escolha:** Em [`widget_editor_dados.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/views/widget_editor_dados.py), na segregação de `campos_principais`, campos denominados `caminho_imagem_capa` são explicitamente ordenados para a primeira posição (índice 0) antes de `nome`.
- **Alternativas consideradas:** Apenas confiar na ordem de declaração no `.proto`. A ordenação explícita na UI é mais resiliente contra futuras alterações no arquivo `.proto`.

### Decisão 3: Orçamento de 1 Megapixel
- **Escolha:** Passar `area_maxima=AREA_MAXIMA_ESCALADA` (1.000.000 px) para o `WidgetCampoImagem` e utilizá-lo no script de extração.
- **Justificativa:** Fotos de capa são destinadas a cartões e cabeçalhos visuais (banners), dispensando o zoom profundo necessário em fotos de vias e mapas de parede. Isso reduz o peso médio de 400 KB para ~100 KB por imagem.

### Decisão 4: Heurística do Script de Extração de Capas
- **Escolha:** O script `extrair_capas_markdown.py`:
  1. Varre arquivos `setor_*.md` e `grupo_*.md` em `database/`.
  2. Ignora arquivos que já possuam `caminho_imagem_capa` no frontmatter.
  3. Localiza a primeira tag de imagem `![alt](caminho)` presente no corpo.
  4. Atribui o caminho relativo a `caminho_imagem_capa` no frontmatter.
  5. Remove a respectiva tag `![alt](caminho)` do corpo Markdown, preservando títulos, tabelas e parágrafos.
  6. Inspeciona a imagem correspondente em disco; se exceder 1 MP, comprime-a para WebP respeitando o teto de 1 MP.

### Decisão 5: Rastreamento em ImagensCroqui e Deploy
- **Escolha:** Atualizar `extrair_caminhos_imagens` em `imagens_croqui.py` e os coletores de caminhos de arquivos externos em `preparar_submissao_lib.py` e `deploy_generated.py`.
- **Justificativa:** Garante que o Undo/Redo do editor reconheça a imagem na RAM, não delete a foto incorretamente durante a edição e gere pacotes `.binarypb` completos com checksums.

## Riscos e Mitigações (Risks / Trade-offs)

- **[Risco: Remoção indevida de imagens que não eram capa]**  
  *Mitigação:* O usuário fará a revisão manual de cada setor diretamente no Editor Aresta, onde a capa agora fica evidente no topo da tela com opção de trocar ou remover em 1 clique.
- **[Risco: Conflito de merge com alterações pendentes em markdowns]**  
  *Mitigação:* O script de extração é idempotente e pode ser reexecutado a qualquer momento em croquis específicos ou em lote.
