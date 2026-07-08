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

Sua tarefa é extrair **todos** os pontos de interesse do mapa. Para isso, examine a imagem com cuidado e extraia as seguintes informações para cada ponto:

* **Id marcado no mapa** (um identificador único).
* **Label textual que está escrita na imagem**. Não deduza labels de outros arquivos; baseie-se apenas na imagem, no OCR, e nos pontos que porventura já existam no `<imagem>.json` (estes são extremamente confiáveis).
* **Geometria delimitadora**. Cada ponto deve ser delimitado pela geometria que melhor descreve sua forma no mapa.

> **Prioridade de Geometrias (Regra de Ouro):** 
> Para manter a consistência visual do projeto, escolha a geometria seguindo a rigorosa ordem de prioridade abaixo:
> 
> 1. **`circulo`** (x, y, raio): Prioridade máxima. Use sempre que o ponto for circular ou tiver dimensões semelhantes no OCR. Se o OCR fornecer uma caixa, e `largura` for próxima de `comprimento`, converta para círculo com raio `(comprimento + largura) / 4`.
> 2. **`quadrado`** (x, y, lado, [angulo_graus_x100]): Use quando a área tiver largura e altura semelhantes, mas for visualmente grafada como um quadrado no mapa.
> 3. **`retangulo`** (x, y, comprimento, largura, [angulo_graus_x100]): Use apenas quando a área de interesse for nitidamente mais larga do que alta ou vice-versa (ex: placas de setor).
> 4. **`poligono`** (coordenadas: [x1, y1, x2, y2, ...]): Útil apenas como último recurso para demarcações completamente irregulares (como áreas livres amorfas demarcadas).

*Detalhe sobre o ângulo (`angulo_graus_x100`)*: Em geometrias com lados retos (retângulo e quadrado), caso a imagem original apresente o ponto de interesse inclinado, você pode rotacionar a área em torno do seu centro `(x,y)`. O valor deve ser a rotação no sentido horário em graus multiplicado por 100 (ex: 35.6° vira 3560).

> [!TIP]
> **Uso do OCR:** 
> Você deve extrair as caixas delimitadoras (`x`, `y`, `comprimento`, `largura`) diretamente de `raw_mapas/<imagem>.ocr_result.json`. Em seguida, adapte esses dados brutos do OCR para a geometria ideal seguindo a hierarquia acima (ex: transformando uma caixa de 40x42 em um `circulo` com raio 20 ou em um `quadrado` de lado 41).
> **Sempre** abra a imagem e cruze com `<imagem>.ocr_result.png` para garantir precisão e capturar itens que o OCR ignorou.

> [!WARNING]
> **Limitações do OCR:**
> O OCR frequentemente falha, ignora itens ou cria caixas partidas. Use o tamanho das marcações vizinhas para estimar as dimensões manualmente quando o JSON não for suficiente.

**Regras Finais de Extração:**
* Não invente pontos de interesse que não existem.
* Não crie pontos de interesse para desenhos soltos (como traços). Todo ponto extraído precisa ter um significado (via, boulder, setor, etc).
* Se um mesmo texto (ex: "2") aparecer repetido no mapa em locais distintos (o que acontece em continuações), extraia todos, diferenciando seus IDs lógicos no JSON (ex: "02_abaixo" e "02_acima"), mas mantendo o `label` idêntico ("2").

Um exemplo de como ficaria a seção de pontos de interesse do arquivo JSON:

```json
{
  "pontos_de_interesse": [
    { "id": "01", "label": "01", "circulo": { "x": 684, "y": 824, "raio": 16 } },
    { "id": "02", "label": "02", "quadrado": { "x": 732, "y": 882, "lado": 35 } },
    { "id": "Mesa", "label": "Mesa", "retangulo": { "x": 876, "y": 547, "comprimento": 48, "largura": 25 } },
    { "id": "Setor_Savassinha", "label": "Setor Savassinha", "retangulo": { "x": 1167, "y": 637, "comprimento": 265, "largura": 25, "angulo_graus_x100": 4500 } },
    { "id": "Livre", "label": "Livre", "poligono": { "coordenadas": [0, 0, 10, 0, 10, 10] } }
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
