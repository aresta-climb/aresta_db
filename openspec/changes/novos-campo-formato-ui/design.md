## Context

No editor do Aresta, os formulários são gerados dinamicamente a partir das anotações do schema Protobuf definido em `croqui.proto`.

Esta mudança resolve duas limitações de usabilidade e ergonomia:
1. **Coordenadas Geográficas (E7)**: Armazenadas como inteiros `sint32` multiplicados por $10^7$ (`latitude` e `longitude`). O editor atualmente renderiza um `QSpinBox` genérico com inteiros (ex: `-198980280`), tornando a edição ilegível e não intuitiva.
2. **Campos de Imagem**: Armazenados como caminhos relativos em string (`caminho_thumbnail` do croqui, `caminho_imagem_mapa` dos mapas). O editor atualmente renderiza um `QLineEdit` sem miniatura, metadados ou suporte a pré-processamento/compressão WebP e navegação para o Editor de Imagens.

O design a seguir foi estritamente estruturado em conformidade com o documento [`PRINCIPIOS.md`](file:///c:/Renato/Devel/aresta-climb/aresta_db/PRINCIPIOS.md).

## Goals / Non-Goals

**Goals:**
- **Conformidade com PRINCIPIOS.md**:
  - **Tudo em Português**: Todo código, funções, variáveis, comentários e arquivos nomeados em português brasileiro.
  - **Library-First**: Criar bibliotecas de domínio puras em `editor/core/` desacopladas de componentes gráficos Qt.
  - **100% de Cobertura e TDD**: Cada arquivo `.py` deve possuir seu respectivo `_test.py` no mesmo diretório com 100% de cobertura.
  - **Testes de Integração em Primeiro Lugar**: Testar os contratos de fronteira entre os widgets, `WidgetEditorDados`, `CroquiModel` e `AreaPrincipal`.
  - **Simplicidade e Anti-Abstração**: Funções diretas e declarativas, sem hierarquias complexas de classes ou factories artificiais.
  - **Edições via Comandos do Histórico**: Todas as mutações de dados na interface passam obrigatoriamente por comandos `QUndoCommand` via `CroquiController`.
- Adicionar novos formatos no enum `CampoFormatoUi`: `LATITUDE_E7`, `LONGITUDE_E7` e `IMAGEM`.
- Adicionar a opção de campo Protobuf `string nome_arquivo_imagem = 50009;`.
- Implementar a biblioteca pura `editor/core/coordenadas.py`:
  - Conversão determinística e bidirecional de/para inteiro E7 ($int(round(float \times 10^7))$ e $int / 10^7$).
  - Formatação e identificação de hemisférios e limites geográficos (Latitude $[-90.0, +90.0]$ e Longitude $[-180.0, +180.0]$).
  - Parser robusto para colagem inteligente de coordenadas (identificando pares decimais, DMS e sufixos cardinais).
- Implementar o componente visual `WidgetCampoCoordenadaE7`:
  - Entrada de ponto flutuante com até 7 casas decimais.
  - Indicador e badge visual da Rosa dos Ventos (`19.8980280° S (Sul)` e `43.5212340° W (Oeste)`).
  - Diálogo leve de confirmação para colagem inteligente com botão de inversão rápida de eixos (Latitude/Longitude).
  - Botão de atalho para abrir o ponto no Google Maps.
- Implementar a biblioteca pura `editor/core/processamento_imagem_campo.py`:
  - Extração de metadados de imagem (dimensões em pixels e tamanho em KB).
  - Sanitização de nomes de arquivos e verificação de conflitos em disco.
  - Conversão e compressão WebP de imagem usando Pillow (RGB/RGBA, área máxima de 4MP e qualidade 85).
- Implementar o componente visual `WidgetCampoImagem`:
  - Pré-visualização da imagem em miniatura com proporção preservada.
  - Exibição de metadados.
  - Ação "Trocar Imagem..." com diálogo de nome (se não fixo) e alerta de conflito.
  - Ação "Abrir no Editor de Imagens" com navegação e foco na `PaginaImagens`.
  - Sincronização automática com a lista de imagens do editor.

**Non-Goals:**
- Não alterar a representação binária e em disco do formato E7 no schema Protobuf nem nos arquivos YAML/Markdown.
- Não substituir a ferramenta completa de edição gráfica de imagens (`WidgetEditorImagens`).

## Decisions

### 1. Separação de Bibliotecas Puras de Lógica (Library-First)
- **Decisão**: Toda a lógica de conversão matemática de E7, validação de limites, parsing de strings de coordenadas, leitura de metadados de imagens, sanitização de nomes e compressão WebP reside em módulos puros Python no pacote `editor/core/` (`coordenadas.py` e `processamento_imagem_campo.py`), completamente independentes de `PyQt6`.
- **Racional**: Permite testar exaustivamente 100% dos cenários de cálculo, bordas e parsing sem necessidade de instanciar contexto de interface gráfica (`QApplication` ou `qtbot`), garantindo velocidade e isolamento conforme o Princípio II (*Library-First*).
- **Alternativas consideradas**: Embutir a lógica de conversão diretamente dentro dos métodos dos widgets PyQt6. Rejeitado por violar o princípio *Library-First* e dificultar a testabilidade unitária isolada.

### 2. Separação de Enums `LATITUDE_E7` e `LONGITUDE_E7`
- **Decisão**: Criar dois enums distintos em `CampoFormatoUi`.
- **Racional**: Latitude possui intervalo restrito $[-90.0, +90.0]$ e pontos cardeais Norte/Sul ($N/S$). Longitude possui intervalo $[-180.0, +180.0]$ e pontos cardeais Leste/Oeste ($E/W$). Ter enums separados no Protobuf torna o schema autoexplicativo e permite validação direta de limites.
- **Alternativas consideradas**: Um único enum `COORDENADA_E7` que deduzisse o eixo pelo nome do campo (`latitude`/`longitude`). Rejeitado por ser frágil caso existam campos com nomenclaturas variadas no futuro.

### 3. Conversão Numérica Exata de E7
- **Decisão**: A UI trabalha com `float` (64-bit IEEE 754) para renderização e edição. A mutação no Model (`CroquiModel`) e Controller (`CroquiController`) continua recebendo inteiros `sint32` em E7.
- **Racional**: O tipo `float` de 64 bits garante 15 a 17 dígitos significativos de precisão. Como coordenadas E7 possuem no máximo 10 dígitos significativos, as operações `val_float = val_int / 10_000_000.0` e `val_int = int(round(val_float * 10_000_000))` são exatas e livres de erros de acumulação.

### 4. Colagem Inteligente com Diálogo de Confirmação e Inversão
- **Decisão**: Ao detectar a colagem de um par de coordenadas (ex: `-19.898028, -43.521234` ou strings com graus DMS), abrir um micro-diálogo exibindo a interpretação de Latitude e Longitude, com botão de inversão rápida de eixos (⇄) e atalho `Enter` para aplicar.
- **Racional**: Diferentes sistemas utilizam ordens distintas (Google Maps usa `Lat, Lon`, GeoJSON/GIS usa `Lon, Lat`). A confirmação em 1 clique previne erros humanos de inversão geográfica.

### 5. Gestão de Nomenclatura e Pré-processamento de Imagens
- **Decisão**:
  - Se o campo Protobuf tiver a anotação `(aresta.nome_arquivo_imagem) = "thumbnail.webp"`, a imagem processada é salva diretamente nesse nome fixo dentro de `database/<croqui>/imagens/`.
  - Se o campo não tiver nome fixo, exibe um diálogo com o nome sugerido (slug sanitizado da imagem original) e alerta visual de sobrescrita caso o arquivo já exista na pasta `imagens/`.
  - O processamento reutiliza a rotina de compressão WebP (conversão para RGB/RGBA, escala para área máxima de 4MP e qualidade 85).

### 6. Mutação Estrita via Histórico (Princípio VII)
- **Decisão**: Qualquer alteração em campo de coordenada ou de imagem feita a partir dos novos widgets deve emitir sinais ou acionar `controller.alterar_primitivo(msg, campo_nome, valor_antigo, valor_novo)`.
- **Racional**: Garante que qualquer edição seja registrada na pilha de histórico (`QUndoCommand`), possibilitando desfazer e refazer de forma consistente.

### 7. Navegação Direta para a Aba do Editor de Imagens
- **Decisão**: Adicionar método na `AreaPrincipal` e `PaginaImagens` para alternar a aba ativa e focar diretamente no arquivo de imagem no `WidgetEditorImagens`.

## Structure

```
aresta_db/
├── aresta_api/proto/
│   └── croqui.proto                                # Schema Protobuf atualizado
├── editor/
│   ├── core/
│   │   ├── coordenadas.py                          # Biblioteca pura de coordenadas E7
│   │   ├── coordenadas_test.py                     # Testes unitários da biblioteca de coordenadas
│   │   ├── processamento_imagem_campo.py           # Biblioteca pura de processamento de imagens
│   │   └── processamento_imagem_campo_test.py      # Testes unitários da biblioteca de imagens
│   └── views/
│       ├── widget_campo_coordenada_e7.py           # Widget de UI para coordenadas E7
│       ├── widget_campo_coordenada_e7_test.py      # Testes unitários e de integração do widget de coordenadas
│       ├── widget_campo_imagem.py                  # Widget de UI para imagens
│       ├── widget_campo_imagem_test.py             # Testes unitários e de integração do widget de imagens
│       ├── widget_editor_dados.py                  # Renderização dos novos formatos
│       └── protobuf_widget_factory.py              # Fábrica de widgets atualizada
```

## Risks / Trade-offs

- **[Risco] Sobrescrita acidental de imagem existente** → **Mitigação**: O diálogo de definição de nome verifica se o arquivo já existe em `database/<croqui>/imagens/` e alerta o usuário com mensagem de confirmação destacada antes de prosseguir.
- **[Risco] Undo de substituição de imagem** → **Mitigação**: O `controller.alterar_primitivo` gerencia o caminho no Protobuf. Ao desfazer, o campo volta a apontar para o caminho anterior, mantendo a integridade do modelo.
- **[Risco] Parser de coordenadas aceitar formatos inesperados** → **Mitigação**: A biblioteca `editor/core/coordenadas.py` será coberta por testes unitários exaustivos testando formatos decimais com vírgula, com ponto, com espaços, sufixos cardinais e graus/minutos/segundos (DMS).
