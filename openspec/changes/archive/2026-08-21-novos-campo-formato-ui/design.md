## Context

No editor do Aresta, os formulários são gerados dinamicamente a partir das anotações do schema Protobuf definido em `croqui.proto`.

Esta mudança resolve duas limitações de usabilidade e ergonomia:
1. **Coordenadas Geográficas (E7)**: Armazenadas como inteiros `sint32` multiplicados por $10^7$ (`latitude` e `longitude`). O editor atualmente renderiza um `QSpinBox` genérico com inteiros (ex: `-198980280`), tornando a edição ilegível e não intuitiva.
2. **Campos de Imagem**: Armazenados como caminhos relativos em string (`caminho_thumbnail` do croqui, `caminho_imagem_mapa` dos mapas). O editor atualmente renderiza um `QLineEdit` sem miniatura, metadados ou suporte a pré-processamento/compressão WebP.

Para garantir que a manipulação de imagens não cause efeitos colaterais no disco antes do salvamento e ofereça suporte completo a Undo/Redo conforme o Princípio VII, introduzimos uma arquitetura de **Buffer de Imagens em RAM** no `CroquiModel`.

## Goals / Non-Goals

**Goals:**
- **Conformidade com PRINCIPIOS.md**:
  - **Tudo em Português**: Todo código, funções, variáveis, comentários e arquivos nomeados em português brasileiro.
  - **Library-First**: Criar bibliotecas de domínio puras em `editor/core/` desacopladas de componentes gráficos Qt.
  - **100% de Cobertura e TDD**: Cada arquivo `.py` deve possuir seu respectivo `_test.py` no mesmo diretório com 100% de cobertura.
  - **Testes de Integração em Primeiro Lugar**: Testar os contratos de fronteira entre os widgets, `WidgetEditorDados`, `CroquiModel`, `AreaPrincipal`, `PaginaImagens` e `PaginaMapas`.
  - **Simplicidade e Anti-Abstração**: Funções diretas e declarativas.
  - **Edições via Comandos do Histórico**: Todas as mutações passam obrigatoriamente por `QUndoCommand` via `CroquiController`.
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
  - Extração de metadados de imagem a partir de bytes ou arquivos (dimensões em pixels e tamanho em KB).
  - Sanitização de nomes de arquivos e verificação de conflitos.
  - Conversão e compressão WebP de imagem para `bytes` em RAM usando Pillow (RGB/RGBA, área máxima de 4MP e qualidade 85).
- Implementar o Buffer de Imagens em RAM no `CroquiModel` e Comando `CmdAlterarCampoImagem`:
  - Armazenamento em `model._imagens_em_memoria: dict[str, bytes]`.
  - Comando `CmdAlterarCampoImagem` gerenciando caminho e bytes na RAM com suporte a Undo/Redo sem tocar no disco.
  - Gravação física atômica no disco apenas no momento de `salvar_croqui()`.
  - Recarregamento automático da `PaginaImagens` e da `PaginaMapas` após o salvamento.
- Implementar o componente visual `WidgetCampoImagem`:
  - Pré-visualização da imagem em miniatura a partir da RAM ou disco com proporção preservada.
  - Exibição de metadados.
  - Ação "Trocar Imagem..." com diálogo de nome (se não fixo) e alerta de conflito.
  - Ação "Abrir no Editor de Imagens" com navegação e foco na `PaginaImagens`.

**Non-Goals:**
- Não alterar a representação binária e em disco do formato E7 no schema Protobuf nem nos arquivos YAML/Markdown.
- Não substituir a ferramenta completa de edição gráfica de imagens (`WidgetEditorImagens`).

## Decisions

### 1. Buffer de Imagens em RAM no `CroquiModel` com Gravação Atômica no Salvamento
- **Decisão**: Ao selecionar ou substituir uma imagem em um campo, a imagem é processada e comprimida para bytes WebP que ficam armazenados em memória dentro de `CroquiModel._imagens_em_memoria`. Nenhum arquivo é escrito ou excluído do disco durante a sessão de edição. Apenas quando o usuário aciona "Salvar" (`salvar_croqui`), os bytes são gravados fisicamente em `database/<croqui>/imagens/`.
- **Racional**:
  - **Zero efeitos colaterais**: Se o usuário fechar o aplicativo sem salvar ou descartar alterações, o disco permanece 100% intocado.
  - **Simetria arquitetural**: Segue o mesmo padrão de `ArquivoMarkdown` e `ArquivoSetor`, onde todo o conteúdo é manipulado em RAM no modelo.
  - **Segurança contra sobrescritas**: Conflitos de nome não destroem arquivos do disco durante testes de imagens.
- **Alternativas consideradas**: Escrever no disco imediatamente e tentar gerenciar arquivos temporários. Rejeitado por gerar complexidade desnecessária de limpeza, risco de arquivos órfãos e quebra do fluxo de Undo/Redo.

### 2. Comando Dedicado de Histórico: `CmdAlterarCampoImagem`
- **Decisão**: Criar a classe `CmdAlterarCampoImagem(QUndoCommand)` em `editor/commands/comandos_protobuf.py` que preserva o caminho antigo, os bytes antigos (se existentes em RAM), o caminho novo e os bytes novos em RAM.
- **Racional**: Permite que o comando `undo()` e `redo()` restaure tanto a referência no Protobuf quanto a pré-visualização gráfica na UI instantaneamente, sem acessar o sistema de arquivos.

### 3. Recarregamento das Páginas de Imagens e Mapas no Salvamento
- **Decisão**: No callback de sucesso do salvamento de croqui na `AreaPrincipal`, invocar:
  1. `self.pagina_imagens.carregar_imagens(caminho_db)` para atualizar a listagem de arquivos da aba Imagens.
  2. `self.pagina_mapas.editor.configurar_lista_mapas()` / recarregamento correspondente na `PaginaMapas` para sincronizar novas imagens de mapas.
- **Racional**: Garante que todas as abas do editor reflitam fielmente o novo estado do disco assim que o salvamento é concluído.

### 4. Separação de Bibliotecas Puras de Lógica (Library-First)
- **Decisão**: Toda a lógica de conversão matemática de E7, validação de limites, parsing de strings de coordenadas, leitura de metadados de imagens, sanitização de nomes e compressão WebP reside em módulos puros Python no pacote `editor/core/` (`coordenadas.py` e `processamento_imagem_campo.py`), completamente independentes de `PyQt6`.
- **Racional**: Permite testar exaustivamente 100% dos cenários de cálculo, bordas e parsing sem necessidade de instanciar contexto de interface gráfica (`QApplication` ou `qtbot`), garantindo velocidade e isolamento conforme o Princípio II (*Library-First*).

### 5. Separação de Enums `LATITUDE_E7` e `LONGITUDE_E7`
- **Decisão**: Criar dois enums distintos em `CampoFormatoUi`.
- **Racional**: Latitude possui intervalo restrito $[-90.0, +90.0]$ e pontos cardeais Norte/Sul ($N/S$). Longitude possui intervalo $[-180.0, +180.0]$ e pontos cardeais Leste/Oeste ($E/W$).

### 6. Conversão Numérica Exata de E7
- **Decisão**: A UI trabalha com `float` (64-bit IEEE 754) para renderização e edição. A mutação no Model (`CroquiModel`) e Controller (`CroquiController`) continua recebendo inteiros `sint32` em E7.
- **Racional**: O tipo `float` de 64 bits garante 15 a 17 dígitos significativos de precisão. Como coordenadas E7 possuem no máximo 10 dígitos significativos, as operações `val_float = val_int / 10_000_000.0` e `val_int = int(round(val_float * 10_000_000))` são exatas e livres de erros de acumulação.

### 7. Colagem Inteligente com Diálogo de Confirmação e Inversão
- **Decisão**: Ao detectar a colagem de um par de coordenadas (ex: `-19.898028, -43.521234` ou strings com graus DMS), abrir um micro-diálogo exibindo a interpretação de Latitude e Longitude, com botão de inversão rápida de eixos (⇄) e atalho `Enter` para aplicar.

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
│   ├── commands/
│   │   ├── comandos_protobuf.py                    # CmdAlterarCampoImagem (QUndoCommand)
│   │   └── comandos_protobuf_test.py               # Testes do comando de imagem
│   ├── models/
│   │   ├── croqui_model.py                         # Buffer _imagens_em_memoria e extração no save
│   │   └── croqui_model_test.py                    # Testes de buffer e persistência de imagens
│   ├── views/
│   │   ├── widget_campo_coordenada_e7.py           # Widget de UI para coordenadas E7
│   │   ├── widget_campo_coordenada_e7_test.py      # Testes unitários e de integração do widget de coordenadas
│   │   ├── widget_campo_imagem.py                  # Widget de UI para imagens
│   │   ├── widget_campo_imagem_test.py             # Testes unitários e de integração do widget de imagens
│   │   ├── widget_editor_dados.py                  # Renderização dos novos formatos
│   │   └── protobuf_widget_factory.py              # Fábrica de widgets atualizada
│   └── legacy_views/
│       ├── area_principal.py                       # Recarregamento de imagens e mapas no salvamento
│       └── area_principal_imagens_integracao_test.py
```

## Risks / Trade-offs

- **[Risco] Uso excessivo de memória com múltiplas imagens** → **Mitigação**: As imagens são comprimidas em WebP antes de serem mantidas na RAM (tamanho típico de 100KB a 400KB por imagem), resultando em consumo desprezível de memória mesmo com dezenas de alterações.
- **[Risco] Parser de coordenadas aceitar formatos inesperados** → **Mitigação**: A biblioteca `editor/core/coordenadas.py` será coberta por testes unitários exaustivos testando formatos decimais com vírgula, com ponto, com espaços, sufixos cardinais e graus/minutos/segundos (DMS).
