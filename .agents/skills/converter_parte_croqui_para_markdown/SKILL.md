---
name: converter_parte_croqui_para_markdown 
description: Converte uma parte de um croqui para arquivo Markdown com YAML Frontmatter.
---

# Converter Parte de Croqui de Escalada para Markdown com YAML Frontmatter

Nessa skill, você irá receber o nome da parte do croqui sendo convertida, que será o nome do arquivo `.md` que será gerado. Além disso, você receberá os números das páginas que devem compor essa parte do croqui.

## 1. Entendendo o conteúdo dessa parte do croqui e fazendo a transcrição inicial.

Leia o arquivo PDF que representa essa parte do croqui (`<parte>.pdf`). Transcreva todas as informações encontradas nessas páginas para o arquivo .md. Dê preferência para as seções estruturadas em YAML Frontmatter caso forem relevantes para a informação sendo transcrita. Alternativamente, preencha o Markdown da página com a informação transcrita.

Instruções durante a conversão:

### 1.1. Partes não-setores e não-grupos

Para partes que não são setores (i.e. não possuem o prefixo `setor_` ou `grupo_`), preencha o conteúdo principalmente na seção markdown do arquivo, transcrevendo toda a informação presente nas páginas. Mantenha em mente:
- Transcreva **TODAS** as informações contidas nas páginas do PDF. Não sumarize, não deixe nada de fora. Transcreva **TODO** o conteúdo textual.
- Caso as páginas possuírem imagens, procure e encontre a imagem correspondente na pasta `raw_pdf_contents/imagens/` e as inclua usando a sintaxe de imagens do Markdown.
- Coloque as imagens próximas ao texto relacionada a elas, e não no fim do arquivo.
- Note que a imagem correta pode ser qualquer uma das imagens na pasta da página, dado que as imagens estão fora de ordem.
- Pode ser necessário inspecionar cada imagem para encontrar a imagem relevante para ser adicionada ao arquivo markdown.
- Se o conteúdo especificar uma legenda para a imagem, essa legenda deve ser escrita na área de alt text para a imagem. Ela será processada apropriadamente depois se estiver no alt text.
- **IMPORTANTE:** Garanta que exista pelo menos uma linha vazia entre imagens consecutivas e entre imagens e textos adjacentes.

### 1.2 Grupos

Para grupos (começando com o prefixo `grupo_`), siga RIGOROSAMENTE o formato da mensagem `Grupo` no código fonte `aresta_api/proto/croqui.proto` para representar a lista de setores na seção YAML. Esse tipo de arquivo será principalmente um arquivo Markdown com as informações do grupo de setores, podendo opcionalmente conter um mapa para localização de cada sub-setor, e então uma lista de sub-setores que podem ser especificados pelo campo `setores` da mensagem `Grupo`. Preencha a mensagem `Grupo` e coloque o caminho para os arquivos `.md` de cada sub-setor, que devem ficar em arquivos Markdown independentes.

### 1.3 Mapas Gerais

Para mapas gerais (nome da parte for `mapas_gerais`), você deve gerar um arquivo `.md` que representa a mensagem `ColecaoDeMapas` do Protobuf. Este arquivo deve conter SOMENTE o YAML frontmatter (sem conteúdo de texto fora dele, ou se houver, será ignorado). Siga RIGOROSAMENTE o formato:
- Preencha a lista `mapas` no frontmatter.
- Para cada imagem na pasta `raw_pdf_contents/imagens/mapas_gerais/` que representa um mapa, adicione um item à lista com o campo `caminho_imagem_mapa` apontando para a imagem (ex: `raw_pdf_contents/imagens/mapas_gerais/pX_iY.webp`).
- Extraia referências visuais de outros setores no mapa, se existirem, preenchendo a lista `referencias`.

### 1.4 Setores
    
Para setores (começando com o prefixo `setor_`), siga RIGOROSAMENTE o formato da mensagem `Setor` no código fonte `aresta_api/proto/croqui.proto` para representar a lista de escaladas na seção YAML. Inclua toda a informação disponível sobre cada escalada:
  - Nome da escalada
  - Dificuldade da escalada (mapeado obrigatoriamente para as enumerações `GrauVia` ou `GrauBoulder` encontradas em `aresta_api/proto/croqui.proto`, e.g., `BR_7A`, `BR_5SUP`, `V7`).
  - **Mapeamentos Especiais de Enumeração:**
    ```yaml
    BR_6C: BR_6SUP
    BR_6B: BR_6_BARRA_6SUP
    BR_6A: BR_6
    BR_5C: BR_5SUP
    BR_5B: BR_5_BARRA_5SUP
    BR_5A: BR_5
    ```
  - Caso a escalada estiver entre dois graus (por exemplo, "7b/c" para via, ou "V7/8" para boulder), use as enumerações BARRA para representar essas graduações (`BR_7B_BARRA_7C`, ou `V7_BARRA_V8`, respectivamente).
  - Contagem de proteções: Parseie string como `"4+2"` gerando explicitamente a sintaxe:
    ```yaml
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 2
    ```
  - Para as escaladas que estiverem marcadas como uma "estrela" ou "diamante", adicione o campo `destaque: true`.
  - Tipo da escalada (use Boulder para boulders, ViaEsportiva para vias inteiramente fixas, ViaMovel para vias móveis ou mistas, e ViaMultiplasEnfiadas para vias com múltiplas enfiadas)
  - Conquistadores
  - Outros campos que fazem parte da mensagem e sub-mensagens de `Escalada` em `croqui.proto`. 
  - Note que vias de múltiplas enfiadas podem possuir um croqui dedicado à própria via. Nesses casos, adicione a imagem do croqui no campo `caminho_imagem_croqui` da mensagem `ViaMultiplasEnfiadas`.
  - Escolha as imagens dentre as imagens em `raw_pdf_contents/imagens/` que representam os mapas setor. Coloque o caminho para cada imagem em uma nova sub-mensagem `mapas`, campo `caminho_imagem_mapa`. Compare o conteúdo visual do pdf com cada imagem individual para decidir as imagens mais representativas para os mapas do setor.
  - **IMPORTANTE:** Para cada escalada listada no setor, extraia a numeração/código que a representa no mapa visual e preencha a lista `referencias` dentro do mapa correspondente. Cada referência deve conter o campo `escalada` (com o nome exato da escalada) e o campo `ids` (uma lista com a numeração encontrada). Exemplo de estrutura no YAML: dentro de `mapas`, adicione `referencias: [{escalada: 'Nome da Via', ids: ['12']}]`. NUNCA coloque IDs de mapa dentro da mensagem da escalada em si.
  - Caso o campo `caminho_imagem_croqui` já for preenchido, não é preciso adicionar nenhuma imagem de mapa na seção Markdown do arquivo, a não ser que seja para mostrar alguma outra parte da imagem (por exemplo foto de uma pessoa escalando).
  - Caso a imagem selecionada for do tipo `pX.webp`, confira se a imagem `pX_i0.webp` é a mesma imagem mas com resolução diferente. Se sim, prefira usar `pX_i0.webp` pois irá ter melhor qualidade e menor tamanho.
  - Quaisquer informação restante que não mapear diretamente para um campo no proto, adicione à área de texto livre do markdown ou ao campo `descricao` da escalada, o que for mais apropriado. Se houverem outras imagens sobre o setor, também incluir elas aqui com a funcionalidade de incluir imagens em Markdown.
  - **IMPORTANTE**: TODA a informação do setor, incluindo partes textuais, deve ser transcrita para algum campo do protobuf ou da área de markdown.
  - Organizar a estrutura hierárquica: `Setores` -> `Escaladas` -> `ViaEsportiva`

## 2. Regras Estritas de Formatação e Sintaxe

> [!WARNING]
> **O YAML DEVE SER PERFEITO:** Você está escrevendo YAML Frontmatter. Qualquer erro de indentação, aspas não fechadas, ou listas mal formatadas no YAML fará com que o parser do Protobuf quebre na etapa final. Revise minuciosamente a sintaxe do seu output.
> - Sempre use aspas em strings no YAML se elas contiverem caracteres especiais (ex: dois pontos `:`).
> - Garanta que a indentação obedeça à estrutura exata do `croqui.proto`.

> [!IMPORTANT]
> **Caminhos de Imagens:** Toda vez que precisar referenciar uma imagem no Markdown, use APENAS caminhos relativos começando a partir da pasta base de imagens. Exemplo correto: `![Mapa Geral](raw_pdf_contents/imagens/p2_i0.webp)`.

## 3. Revisão Final (Self-Correction)

Antes de finalizar sua tarefa, você **DEVE** reler o arquivo `.md` que você acabou de criar.
1. **Sintaxe YAML:** Verifique visualmente se a estrutura YAML está alinhada e as aspas estão corretas.
2. **Imagens:** Confira se as imagens escolhidas são as mais representativas e os caminhos estão perfeitamente formatados.
3. **Integralidade:** Certifique-se de que *nenhuma* informação do PDF original foi omitida.
Se encontrar qualquer problema sintático, edite o arquivo e corrija de imediato antes de devolver a resposta.

## Quando usar essa habilidade

Use essa habilidade quando precisar converter uma parte de um croqui para arquivo Markdown com YAML Frontmatter.
