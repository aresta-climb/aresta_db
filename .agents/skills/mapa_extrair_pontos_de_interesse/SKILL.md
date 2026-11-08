---
name: mapa_extrair_pontos_de_interesse
description: Extrai pontos de interesse de um mapa diretamente no Editor Aresta usando aresta_renderizar_mapa e aresta_alterar_campo.
---

# Extrair Pontos de Interesse de um Mapa (100% via MCP)

Um mapa é uma imagem que representa graficamente os pontos de interesse (POIs) de um setor, grupo ou escalada individual — incluindo números de vias/boulders, trilhas, acessos, paradas e agarras-chave. O objetivo desta skill é extrair todos os pontos de interesse do mapa e suas coordenadas `(x, y)` diretamente na árvore Protobuf do **Editor Aresta** via MCP, sem uso de `PaddleOCR` e sem edição manual de arquivos JSON/Markdown.

> [!CAUTION]
> **Operação Exclusiva via MCP (`editor-aresta`):**
> - **NUNCA** crie ou edite arquivos em `raw_mapas/*.json` ou `.md` no disco, nem execute scripts Python de OCR no terminal.
> - Utilize exclusivamente `aresta_renderizar_mapa`, `aresta_obter_arvore`, `aresta_alterar_campo` e `aresta_vincular_referencia_mapa`.

---

## INPUT ESPERADO

Você receberá do Agente Orquestrador:
- `id_croqui`: Identificador do croqui aberto no Editor Aresta.
- `alvo_mapa`: Endereço do `Mapa` na árvore Protobuf (ex: `"<uid_setor>.mapas.0"`, `"<uid_escalada>.mapas.0"` ou `"picos[0].mapas_gerais.conteudo.mapas.0"`).
- Contexto do mapa: se pertence a um `Setor`/`Grupo`/`ColecaoDeMapas` (`pertence_a_escalada: false`) ou a uma `Escalada` específica (`pertence_a_escalada: true`), bem como a lista de escaladas/setores (`uid` e `nome`) daquele contêiner para vinculação das `referencias`.

---

## 1. O Que é um Ponto de Interesse

### 1.1. Mapas de Setor, Grupo ou Mapas Gerais (`pertence_a_escalada: false`)
- Identificadores numéricos ou alfanuméricos de vias e boulders (ex: `"01"`, `"02"`, `"15"`, `"A"`, `"B"`).
- Indicações para outros setores ou trilhas (ex: `"Setor Savassinha"`, `"Trilha"`, `"Acesso"`).
- Pontos de apoio ou referência (ex: `"Estacionamento"`, `"Mesa"`, `"Ponte"`, `"Camping"`).

### 1.2. Mapas Específicos de Escaladas (`pertence_a_escalada: true`)
Quando o mapa pertence a `escaladas[].mapas` (close-up de boulder ou topo vertical dedicado a uma única via):
- **Pontos de Início / Saída**: Marcações de largada, agarras iniciais de mãos/pés, saída sentada (ex: `"Start"`, `"Sit-start"`, `"Saída"`).
- **Pontos de Finalização / Topo**: Agarras finais, paradas ou cume (ex: `"Top"`, `"Fim"`, `"Parada"`, `"Cume"`).
- **Passagens-Chave**: Movimentos cruciais (ex: `"Crux"`, `"Dinâmico"`).
- **Proteções e Paradas Técnicas**: Chapeletas, grampos, proteções móveis ou paradas intermediárias (ex: `"P1"`, `"P2"`, `"Chapeleta"`).

---

## 2. Prioridade de Geometrias (Regra de Ouro)

Cada `PontoDeInteresse` em `croqui.proto` possui `uid`, `rotulo` e exatamente uma geometria do `oneof tipo` (`circulo`, `quadrado`, `retangulo` ou `poligono`). Siga rigorosamente esta ordem de prioridade:

1. **`circulo`** (`{"x": int, "y": int, "raio": int}`): **Prioridade máxima**. Use sempre que o marcador for circular ou aproximadamente quadrado/compacto (ex: números de vias `"01"`, `"02"`, círculos numerados).
2. **`quadrado`** (`{"x": int, "y": int, "lado": int, "angulo_graus_x100": int}`): Use quando a marcação for visualmente desenhada como um quadrado no mapa.
3. **`retangulo`** (`{"x": int, "y": int, "comprimento": int, "largura": int, "angulo_graus_x100": int}`): Use apenas quando o rótulo ou placa for nitidamente mais largo que alto (ex: placas de texto `"Setor Savassinha"` ou `"Estacionamento"`).
4. **`poligono`** (`{"coordenadas": [x1, y1, x2, y2, ...]}`): Último recurso apenas para áreas irregulares demarcadas no mapa.

> [!NOTE]
> **Rotação (`angulo_graus_x100`)**: Em `quadrado` e `retangulo`, se o texto/caixa estiver inclinado na imagem original, informe a rotação no sentido horário em graus multiplicada por `100` (ex: `35.6°` → `3560`).

---

## 3. Fluxo de Extração via `aresta_renderizar_mapa` e `aresta_alterar_campo`

### Passo 1: Inspecionar o Mapa com Grade Métrica e Sementes Vetoriais (`aresta_renderizar_mapa`)
Chame `aresta_renderizar_mapa`:
```json
{
  "alvo": "<alvo_mapa>",
  "incluir_recortes": false,
  "id_croqui": "<id_croqui>"
}
```
A ferramenta retorna blocos intercalados `[Texto, Imagem]`:
- **Bloco 0 (`text`)**: JSON contendo:
  - `largura` e `altura` exatas da imagem em pixels.
  - `pontos_de_interesse`: lista de POIs já existentes no mapa (se houver). **Preserve rigorosamente o `uid` de qualquer ponto já existente e confiável.**
  - `candidatos_vetoriais`: textos e elementos vetoriais extraídos diretamente do PDF via `PyMuPDF`, já convertidos para coordenadas de pixel `(x, y)` da imagem do mapa!
- **Bloco 1 (`image`)**: Imagem completa do mapa renderizada pelo Editor Aresta com:
  - **Grade métrica semitransparente a cada `100px`** (e linhas secundárias a cada `50px`).
  - **Réguas graduadas nas bordas superior (`X`) e esquerda (`Y`)** de `0` até `largura`/`altura`.
  - Eventuais POIs já cadastrados desenhados em vermelho.

### Passo 2: Determinar Coordenadas `(x, y)` e Rótulos de Todos os POIs
1. **Aproveite os `candidatos_vetoriais` (`PyMuPDF`)**: Quando o PDF original possuía textos vetoriais sobre a foto, `candidatos_vetoriais` já fornece o texto e a caixa/centro `(x, y)` exatos em pixels. Confirme visualmente na imagem do Bloco 1 quais candidatos correspondem a POIs reais do mapa.
2. **Leitura Visual pela Grade Métrica (`100px`) e Réguas (`X`/`Y`)**: Para marcadores desenhados diretamente no bitmap da imagem (ou ignorados na camada vetorial), localize o marcador na imagem do Bloco 1 e leia sua coordenada `(x, y)` diretamente cruzando as linhas de grade de `100px`/`50px` e as réguas graduadas do topo (`X`) e da esquerda (`Y`).
3. **Regras de Rótulo (`rotulo`)**:
   - Preencha `rotulo` exatamente com o que está grafado na imagem (ex: `"01"`, `"02"`, `"Mesa"`).
   - Se o mesmo número aparecer mais de uma vez na imagem (ex: início e continuação da via `"02"`), extraia ambos os pontos com `"rotulo": "02"` (cada um receberá seu próprio `uid` único e ambos poderão ser vinculados em `pontos_uids` daquela escalada).
   - Não crie POIs para linhas de traçado soltas sem rótulo/símbolo identificador.

### Passo 3: Gravar os POIs Atomicamente (`aresta_alterar_campo`)
Envie a lista completa de `pontos_de_interesse` em uma única chamada atômica para `aresta_alterar_campo`:
```json
{
  "alvo": "<alvo_mapa>",
  "id_croqui": "<id_croqui>",
  "campo": "pontos_de_interesse",
  "valor": [
    {
      "rotulo": "01",
      "circulo": { "x": 684, "y": 824, "raio": 18 }
    },
    {
      "rotulo": "02",
      "circulo": { "x": 732, "y": 882, "raio": 18 }
    },
    {
      "rotulo": "Setor Savassinha",
      "retangulo": { "x": 1167, "y": 637, "comprimento": 240, "largura": 28, "angulo_graus_x100": 4500 }
    }
  ]
}
```
> [!IMPORTANT]
> Se o mapa já possuía pontos com `uid`, inclua `"uid": "<uid_existente>"` nos itens correspondentes para preservá-los. Para pontos novos, omita `"uid"` e o Editor Aresta gerará NanoIDs automaticamente.

### Passo 4: Vincular Referências (`aresta_vincular_referencia_mapa`) e Conferir Recortes
1. Chame `aresta_obter_arvore(alvo=alvo_mapa, id_croqui=id_croqui)` para ler os `uid`s atribuídos a cada ponto em `pontos_de_interesse`.
2. Para cada escalada (ou setor, em mapas gerais/grupos) representada no mapa, vincule seu `alvo_uid` aos `pontos_uids` correspondentes usando `aresta_vincular_referencia_mapa(alvo=alvo_mapa, alvo_uid="<uid_escalada>", pontos_uids=["<uid_poi>"], id_croqui=id_croqui)` (ou atualize a lista `referencias` via `aresta_alterar_campo`).
3. Em seguida, aplique imediatamente a skill `@mapa_corrigir_pontos_de_interesse` chamando `aresta_renderizar_mapa(alvo=alvo_mapa, incluir_recortes=True, id_croqui=id_croqui)` para refinar o enquadramento de cada POI com os recortes de mira relativa (`-50px..+50px`).

## Quando usar essa habilidade

Use essa habilidade quando precisar extrair os pontos de interesse de um mapa de setor, grupo, mapa geral ou escalada diretamente no Editor Aresta via MCP.
