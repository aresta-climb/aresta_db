---
name: mapa_corrigir_pontos_de_interesse
description: Refina e corrige a localização dos pontos de interesse de um mapa via MCP usando os recortes com mira relativa de aresta_renderizar_mapa.
---

# Corrigir e Refinar Pontos de Interesse de um Mapa (100% via MCP)

O objetivo desta skill é inspecionar visualmente e ajustar com precisão cirúrgica as coordenadas `(x, y)` e dimensões de todos os pontos de interesse (`pontos_de_interesse`) de um `Mapa` no **Editor Aresta** utilizando a ferramenta MCP `aresta_renderizar_mapa` e seus recortes ampliados com mira relativa (`-50px` a `+50px`).

> [!CAUTION]
> **Proibição de Scripts Legados e Arquivos JSON:**
> - **NUNCA** procure ou execute `visualizar_mapa_processado.py` nem edite arquivos em `raw_mapas/`.
> - Toda visualização e todo ajuste de coordenadas acontecem em memória no Editor Aresta via `aresta_renderizar_mapa` e `aresta_alterar_campo`.

---

## 1. Como Funciona a Inspeção com `aresta_renderizar_mapa`

Chame a ferramenta `aresta_renderizar_mapa` com `incluir_recortes=True`:
```json
{
  "alvo": "<alvo_mapa>",
  "incluir_recortes": true,
  "id_croqui": "<id_croqui>"
}
```
*(Dica: se você estiver refinando apenas alguns pontos específicos após uma primeira rodada, pode passar `"uids_pois": ["<uid_1>", "<uid_2>"]` para receber apenas os recortes daqueles POIs).*

`aresta_renderizar_mapa` retorna uma **lista intercalada de blocos `[Texto, Imagem]`**:
1. **Bloco 0 (`text`)**: Metadados gerais do mapa (`largura`, `altura`, `total_pois`, `candidatos_vetoriais`).
2. **Bloco 1 (`image`)**: Visão geral completa do mapa com **grade métrica semitransparente a cada `100px`** (`50px` secundária), **réguas graduadas nas bordas (`X` e `Y`)** e todos os POIs demarcados em vermelho.
3. **Pares `[Texto, Imagem]` para cada POI (`POI #1`, `POI #2`, ...)**:
   - **Bloco de Texto (`content[2*i + 2]`)**: Identifica explicitamente o ponto:
     `POI #1 | uid=xK9mP2qR | rotulo='01' | tipo=circulo | centro=(684, 824) | geometria={"x": 684, "y": 824, "raio": 18}`
   - **Bloco de Imagem (`content[2*i + 3]`)**: Recorte ampliado de `120x120px` (escalado 2x para `240x240px`) centrado exatamente em `(cx, cy)` contendo:
     - **Mira central verde/azul em `(0, 0)`** (indicando onde está o `(x, y)` atual do POI).
     - **Contorno vermelho da geometria atual** do POI.
     - **Réguas relativas nas bordas variando de `-50px` a `+50px`** (com marcações a cada `10px`).

---

## 2. Loop de Refinamento Visual com a Mira Relativa (`-50px` a `+50px`)

> [!IMPORTANT]
> **Iteração Visual até o Enquadramento Perfeito:**
> Analise cada par `[Texto do POI, Imagem do Recorte]` retornado por `aresta_renderizar_mapa`:

1. **Verifique o Centro `(0, 0)` no Recorte**:
   - O texto ou número real na foto da parede está centrado exatamente no cruzamento `(0, 0)` da mira?
   - **Se estiver deslocado dentro do recorte**: Leia nas réguas relativas das bordas superior (`dx`) e esquerda (`dy`) quantos pixels o centro real do texto está deslocado em relação a `(0, 0)`.
     - Exemplo: se o número `"01"` aparece na marca `+14` da régua horizontal superior e `-8` da régua vertical esquerda, então o novo centro exato é:
       `novo_x = x_atual + 14`
       `novo_y = y_atual - 8`
   - **Se o texto não aparecer dentro do recorte (`> 60px` de erro)**: Olhe para a imagem completa com grade métrica (`Bloco 1`), localize onde o rótulo realmente está usando as réguas absolutas `X`/`Y` de `100px`, e anote a nova coordenada `(x, y)`.

2. **Verifique o Tamanho e a Rotação da Geometria Vermelha**:
   - O círculo, quadrado ou retângulo vermelho envolve de forma justa apenas o rótulo/símbolo do ponto?
   - Se estiver largo ou apertado demais, ajuste `raio` (em `circulo`), `lado` (em `quadrado`) ou `comprimento`/`largura` (em `retangulo`) usando a escala de `10px` das réguas relativas do recorte.
   - Se for um `retangulo` ou `quadrado` sobre um texto inclinado, ajuste `angulo_graus_x100` (graus no sentido horário × 100) para alinhar com a inclinação do texto.

3. **Aplique os Ajustes via `aresta_alterar_campo` (Preservando `UID`s)**:
   - Você pode atualizar um POI individual diretamente pelo seu `uid`:
     ```json
     {
       "alvo": "<uid_poi>",
       "id_croqui": "<id_croqui>",
       "campos": {
         "rotulo": "01",
         "circulo": { "x": 698, "y": 816, "raio": 16 }
       }
     }
     ```
   - Ou atualizar todos os POIs do mapa em uma única transação atômica passando a lista completa para `aresta_alterar_campo(alvo=alvo_mapa, campo="pontos_de_interesse", valor=[...], id_croqui=id_croqui)` — **lembrando sempre de manter o campo `"uid"` de cada ponto existente**.

4. **Re-verifique com `aresta_renderizar_mapa`**:
   - Chame novamente `aresta_renderizar_mapa(alvo=alvo_mapa, incluir_recortes=True, uids_pois=[...], id_croqui=id_croqui)` para confirmar que os pontos ajustados agora estão perfeitamente centrados na mira `(0, 0)` e bem enquadrados.
   - Repita até que **100% dos pontos de interesse** estejam centrados e justos ao redor de seus rótulos.

## Quando usar essa habilidade

Use essa habilidade sempre que precisar verificar e corrigir o posicionamento e o dimensionamento dos pontos de interesse de um mapa no Editor Aresta via MCP.
