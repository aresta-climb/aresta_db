# previa-pull-request Specification

## Purpose

Provê a compilação, comparação semântica/visual contra a branch base, geração de página interativa `resumo.html` e publicação de artefatos de Pull Requests em pasta dedicada no Cloudflare R2 (`serving.arestaclimb.com/pr/<id>/`) para revisão no aplicativo móvel e no navegador.

## Requirements

### Requirement: Publicação de Build de Pull Request no Armazenamento de Serving
O sistema MUST publicar os artefatos compilados dos croquis modificados em uma Pull Request no caminho dedicado `pr/<numero_pr>/` do bucket de serving (`serving.arestaclimb.com`), incluindo `indice.binarypb`, `indice.yaml`, `catalogo.db`, `arquivos_serving.yaml`, `thumbnails/<id>.webp`, `<id>/compilado.binarypb`, `<id>/imagens/*.webp` e `<id>/anexos/*`.

#### Scenario: Upload de artefatos compilados de uma Pull Request válida
- **WHEN** a validação da Pull Request concluir sem erros para um ou mais croquis modificados
- **THEN** o sistema publica todos os arquivos gerados da compilação sob o prefixo `pr/<numero_pr>/` no bucket R2 com os tipos MIME apropriados
- **AND** remove do prefixo `pr/<numero_pr>/` quaisquer arquivos órfãos de execuções anteriores da mesma Pull Request que não pertençam mais à compilação atual

#### Scenario: Preservação de imagens base modificadas ou removidas
- **WHEN** uma imagem de mapa, capa, thumbnail ou Markdown presente na branch base tiver seu conteúdo binário (SHA-256) modificado ou for removida na Pull Request
- **THEN** o sistema publica uma cópia da versão da branch base dessa imagem em `pr/<numero_pr>/_base/<id>/<caminho_imagem>` para viabilizar a comparação visual "Antes vs. Depois" mesmo para croquis ainda não publicados em produção

### Requirement: Comparação Semântica de Croquis por Identificador Universal (UID)
O sistema MUST comparar o estado compilado de cada croqui modificado na Pull Request com o estado correspondente na branch base utilizando o identificador universal (`uid`) de cada entidade (Pico, Grupo, Setor, Escalada, Mapa e Ponto de Interesse).

#### Scenario: Entidade renomeada ou editada mantendo o mesmo UID
- **WHEN** um setor ou escalada tiver seu nome, grau, extensão, conquistadores ou descrição alterados na Pull Request preservando o mesmo `uid`
- **THEN** o diff semântico classifica a entidade como `modificada` (e não como uma remoção seguida de adição), listando cada campo alterado com o valor anterior e o valor novo

#### Scenario: Croqui inteiramente novo na Pull Request
- **WHEN** um croqui modificado na Pull Request não existir na branch base
- **THEN** o diff semântico classifica o croqui como `novo`, contabilizando todas as suas entidades (picos, grupos, setores, escaladas, mapas e imagens) como adicionadas

### Requirement: Relatório Interativo HTML de Mudanças (`resumo.html`)
O sistema MUST gerar um arquivo autocontido `resumo.html` e publicá-lo em `pr/<numero_pr>/resumo.html`, apresentando o resumo visual e estrutural das alterações da Pull Request juntamente com os controles de abertura no aplicativo móvel.

#### Scenario: Visualização de alterações de traçados e pontos em mapas sem alteração da foto
- **WHEN** os pontos de interesse ou referências de um mapa forem adicionados, movidos ou removidos na Pull Request sem alteração nos pixels da imagem do mapa
- **THEN** o `resumo.html` renderiza a imagem `.webp` do mapa com uma camada vetorial `<svg>` interativa sobreposta que destaca pontos/traçados adicionados em verde, pontos movidos em amarelo com seta tracejada da coordenada anterior para a nova, e pontos removidos em vermelho, oferecendo seletores para alternar entre os modos `Diff`, `Antes`, `Depois` e `Ocultar`

#### Scenario: Visualização de mapa cuja imagem sofreu corte, máscara ou substituição
- **WHEN** o arquivo de imagem de um mapa tiver seu hash SHA-256 ou suas dimensões alteradas na Pull Request
- **THEN** o `resumo.html` sinaliza a alteração de resolução/tamanho da imagem do mapa e apresenta a comparação nos modos `Lado a Lado` (imagem base com SVG antigo vs. imagem nova com SVG novo) e `Slider Cortina`

#### Scenario: Comparação visual de imagens de capa, thumbnail e Markdown
- **WHEN** imagens de capa, thumbnail ou fotos referenciadas em textos Markdown forem adicionadas, modificadas ou removidas na Pull Request
- **THEN** o `resumo.html` exibe uma galeria de alterações de imagens indicando onde cada imagem é utilizada, suas dimensões e peso em KB, e um comparador visual `Antes vs. Depois` para as imagens modificadas

#### Scenario: Abertura rápida no aplicativo a partir do relatório HTML
- **WHEN** um revisor abrir o `resumo.html` no navegador do computador ou celular
- **THEN** a página exibe o código formatado da Pull Request (ex: `pr00-0042`), um botão para copiá-lo, o QR Code em SVG apontando para `https://previa.arestaclimb.com/<codigo_pr>` e um botão de ação direta para abrir o croqui no aplicativo Aresta Climb
