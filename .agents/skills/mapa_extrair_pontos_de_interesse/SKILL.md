---
name: mapa_extrair_pontos_de_interesse 
description: Extrai pontos de interesse de um mapa.
---

# Mapa extrair pontos de interesse 

Um mapa é uma imagem que representa graficamente de maneira reduzida e simplificada os pontos de interesse de um setor de escalada, incluindo vias, boulders, trilhas, acesso, etc. O objetivo dessa skill é extrair os pontos de interesse no mapa e suas coordenadas (x, y) na imagem.

## INPUT ESPERADO
Para essa skill, você **DEVE** receber e operar com os seguintes caminhos:
- Caminho da `imagem` do mapa de um setor na pasta `imagens`
- Arquivo `raw_mapas/<imagem>.json` com metadados. Esse arquivo *já pode conter pontos de interesse*. Caso contiver, eles são *muito confiáveis*, preserve-os como estão durante a conversão.
- Resultados do OCR em JSON e PNG: `raw_mapas/<imagem>.ocr_result.json` e `raw_mapas/<imagem>.ocr_result.png`

**Você trabalhará exclusivamente com estes arquivos.**

## OUTPUT ESPERADO
O arquivo JSON `raw_mapas/<imagem>.json` estritamente formatado e populado com os pontos corretamente identificados.

## 1. O que é um ponto de interesse

Um ponto de interesse é qualquer elemento do mapa que possa ser útil para o escalador, como:
* Id de vias
* Id de boulders
* Indicações para outros setores ou trilhas, possivelmente com setas
* Outras áreas de interesse no mapa, como pontes, túneis, mesas, etc.

Normalmente os pontos de interesse estão marcados no mapa com um símbolo (como um ponto, quadrado, seta, etc) e uma descrição textual (como "01", "02", "03", "X", "y", "Z", "Ponte", "Setor Y", etc).

## 2. Extraindo pontos de interesse 

Sua tarefa é extrair **todos** os pontos de interesse do mapa. Para isso, examine a imagem com cuidado, faça uma lista de pontos de interesse completa e extraia as seguintes informações para cada ponto de interesse na imagem:
* Id marcado no mapa
* Label textual **que está escrita na imagem** desse ponto. Não utilize outros arquivos para inferir labels, utilize apenas o conteúdo da imagem e o arquivo `<imagem>.json`. Note que pontos de interesse já podem estar presentes no arquivo `<imagem>.json`, e, se presentes, serão extremamente confiáveis.
* Você pode representar as detecções como retangulos ou circulos. Prefira a representação mais próxima ao conteúdo do mapa. Normalmente isso significa usar círculos, particularmente se o ponto de interesse estiver envolto em um círculo no mapa. Porém, use retângulos caso a detecção seja claramente retangular ou se o ponto de interesse estiver envolto em uma caixa quadrada/retangular. Exemplos:
    * Bounding circle do ponto de interesse: **x, y, raio** do círculo 
    * Bounding box retangular do ponto de interesse:
        * **x, y**: Coordenadas do **centro** da detecção em pixels.
        * **comprimento, largura**: Dimensões da caixa em pixels.
        * **angulo_graus_x100**: Campo opcional, apenas use caso o ponto de interesse seja inclinado. Representado por um ângulo de inteiro rotação em graus multiplicado por 100, no sentido horário, partindo do eixo x positivo, relativo ao centro do retângulo. Por exemplo, 35.6 graus vira 3560.

> [!TIP]
> **Comparação Visual de OCR:** Você pode e deve extrair as bounding boxes (*x, y, comprimento, largura*) diretamente do arquivo `<imagem>.ocr_result.json`. Caso comprimento e largura forem próximos, converta para bounding circle com raio `(comprimento + largura) / 4`.
> **Obrigatório:** Utilize sua habilidade de ver arquivos (`view_file` ou equivalente que retorne a imagem) para visualizar `<imagem>.ocr_result.png` e comparar fisicamente o resultado do texto com a imagem original para fechar boxes super precisos.

> [!WARNING]
> Os arquivos de detecção OCR podem falhar. Pode faltar itens ou eles estarem parciais. Mesmo assim, olhe o tamanho das marcações ao redor para **estimar** você mesmo o centro e as dimensões se não achar o json. O preenchimento da `box` é estritamente manual se o OCR errar.

* Não crie pontos de interesse para elementos que não estejam no mapa.
* Não crie pontos de interesse para desenhos no mapa (por exemplo traços). Os pontos de interesse devem ter algum significado.
* Caso houverem mais de um ponto de interesse com o mesmo texto (por exemplo, "2" aparecendo duas vezes no mapa), nomeie-os com labels iguais mas ids diferentes, por exemplo "02_abaixo" e "02_acima".

Um exemplo de como ficaria a seção de pontos de interesse do arquivo JSON:

```json
{
  "pontos_de_interesse": [
    { "id": "01", "label": "01", "circular": { "x": 684, "y": 824, "raio": 16 } },
    { "id": "02", "label": "02", "box": { "x": 732, "y": 882, "comprimento": 35, "largura": 35 } },
    { "id": "Mesa", "label": "Mesa", "box": { "x": 876, "y": 547, "comprimento": 48, "largura": 25 } },
    { "id": "Setor_Savassinha", "label": "Setor Savassinha", "box": { "x": 1167, "y": 637, "comprimento": 265, "largura": 25, "angulo_graus_x100": 4500 } },
  ]
}
```

## 3. Conferindo e Auto-Validando (Sanity Check)

> [!IMPORTANT]
> **Loop de Validação Rigorosa:** O OCR costuma ser falho e ambiguidades visuais são comuns. 
> 1. Se o OCR retornar um texto quebrado ou ilegível, não confie cegamente. Use o contexto visual da imagem e outras vias ao redor para **deduzir logicamente** o ID ou Label correto.
> 2. Conte mentalmente e anote quantos pontos de interesse existem visualmente no mapa da imagem.
> 3. Conte quantas entradas você acabou de registrar no arquivo `raw_mapas/<imagem>.json`.
> 4. **Os números batem perfeitamente?** Volte à imagem e procure em todos os cantos. Se algum estiver faltando, adicione. Se houver sobras, remova os falsos positivos. Só finalize quando tiver certeza que cobriu 100% da imagem.

## 4. Quando usar essa habilidade

Use essa habilidade quando precisar extrair pontos de interesse de um mapa de um setor de escalada.
