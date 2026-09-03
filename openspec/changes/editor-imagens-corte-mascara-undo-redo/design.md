## Context

O Editor de Imagens (`WidgetEditorImagens`) permite visualizar e tratar fotos e croquis brutos (recortes, rotações e ocultação de marcas/textos indesejados). No entanto, o widget foi originalmente concebido com lógica de manipulação gráfica acoplada diretamente à interface gráfica e mantendo estados locais (`PageState`), onde transformações eram aplicadas diretamente em instâncias locais da biblioteca Pillow (`PIL.Image`) e caixas visuais flutuantes (`CropBoxItem`, `MaskBoxItem`).

Essa arquitetura violava princípios fundamentais do projeto:
1. **Princípio II (Library-First)**: Não havia uma biblioteca independente e pura para executar as transformações de rotação, corte e preenchimento de máscaras a partir de bytes.
2. **Princípio VII (Edições de Estado via Comandos do Histórico)**: Rotações, cortes e máscaras não geravam comandos na pilha `QUndoStack` do `GerenciadorHistorico`, inviabilizando o Desfazer/Refazer e deixando o editor suscetível a perdas de estado em falhas inesperadas.
3. **Princípio VI (Simplicidade)**: O corte exigia manipular alças de uma caixa permanente sobre a imagem, enquanto as máscaras dependiam de botões redundantes ("Limpar Máscaras" e "Resetar") para contornar a ausência de histórico funcional.

## Goals / Non-Goals

**Goals:**
- **Princípio II (Library-First)**: Criar a biblioteca pura e independente `editor/core/transformacoes_imagem.py` (com `transformacoes_imagem_test.py`) para encapsular todas as operações com imagens em bytes WebP.
- **Princípio VII (Edições via Histórico)**: Integrar 100% das mutações visuais do Editor de Imagens à pilha global de histórico (`QUndoStack` / `GerenciadorHistorico`) via `CroquiController.substituir_imagem` e `CmdSubstituirImagemMemoria`.
- **Modo Cortar por Seleção**: Implementar seleção direta por arrasto de área (*rubber band*), realizando o corte imediatamente ao soltar o mouse e limpando a cena gráfica de caixas estáticas.
- **Modo Máscara Direto**: Implementar fluxo de conta-gotas seguido de desenho de retângulo, preenchendo diretamente a imagem em memória RAM com registro atômico no histórico.
- **Princípio I (Tudo em Português)**: Garantir nomenclatura 100% em português brasileiro em todos os módulos, métodos, variáveis e testes.
- **Princípio III, IV e V (TDD e Cobertura 100%)**: Escrever testes de integração em primeiro lugar, seguidos por testes unitários em ciclo TDD Vermelho-Verde-Refatorar, assegurando 100% de cobertura.

**Non-Goals:**
- Implementar ferramentas de desenho vetorial livre ou traçado de vias nesta view (pertencem ao Editor de Mapas).
- Implementar filtros avançados de cor, brilho, contraste ou algoritmos generativos.

## Decisions

### 1. Criação da Biblioteca Pura `editor/core/transformacoes_imagem.py` (Princípio II)
- **Decisão**: Isolar todas as operações sobre matrizes de pixels em uma biblioteca pura que recebe e retorna `bytes` (WebP), sem qualquer dependência de classes do PySide6/Qt:
  - `rotacionar_imagem_bytes(bytes_imagem: bytes, graus: int) -> bytes`
  - `cortar_imagem_bytes(bytes_imagem: bytes, retangulo: Tuple[int, int, int, int]) -> bytes`
  - `aplicar_mascara_bytes(bytes_imagem: bytes, retangulo: Tuple[int, int, int, int], cor_rgb: Tuple[int, int, int]) -> bytes`
  - `obter_cor_pixel(bytes_imagem: bytes, x: int, y: int) -> Tuple[int, int, int]`
- **Vantagens**:
  - Testabilidade 100% independente do ambiente gráfico.
  - Reutilização simples em scripts CLI, testes ou outros controladores.

### 2. Reutilização de `CmdSubstituirImagemMemoria` como Comando Canônico de Imagem (Princípio VII)
- **Decisão**: Toda ação executada na interface gráfica invocará a biblioteca pura e despachará `CroquiController.substituir_imagem(caminho_relativo, bytes_novos, context_path=f"page:imagens/file:{nome_arquivo}")`.
- **Vantagens**:
  - Registra o comando na pilha `QUndoStack` do `GerenciadorHistorico`.
  - Habilita `Ctrl+Z` (Desfazer) e `Ctrl+Y` (Refazer) para todas as operações.
  - Mantém compatibilidade com a persistência de segurança no diário (`diario_pendente.bin`) e persistência final em disco (`extrair_arquivos_e_serializar`).
  - Emite o sinal `imagem_alterada` para atualizar reativamente abas de Mapas e Dados.

### 3. Modo Cortar por Seleção Retangular Ativa (*Rubber Band Selection*)
- **Decisão**: 
  - Ao clicar no botão `✂ Cortar`, a view entra no modo de corte (cursor muda para `CrossCursor`).
  - O usuário clica e arrasta para demarcar a área desejada sobre o visualizador.
  - Ao soltar o mouse: se a seleção for válida ($> 10\times 10$ px), as coordenadas de cena são mapeadas para os pixels da imagem, o recorte é efetuado via `cortar_imagem_bytes`, os novos bytes são despachados para o controller e o modo de corte é finalizado.
  - Cancelamento via tecla `Escape` ou novo clique em `✂ Cortar`.

### 4. Modo Máscara com Conta-gotas e Preenchimento Imediato
- **Decisão**:
  - O usuário aciona `🎨 Máscara`.
  - Passo 1: O cursor de conta-gotas permite clicar em qualquer pixel da imagem para capturar a cor de preenchimento (`obter_cor_pixel`).
  - Passo 2: O usuário clica e arrasta um retângulo sobre a marca a ser oculta.
  - Ao soltar o mouse, o retângulo é preenchido via `aplicar_mascara_bytes` e despachado via `substituir_imagem`.
  - Cada retângulo vira uma entrada atômica na pilha de histórico (`Ctrl+Z`).

### 5. Remoção de Controles e Elementos Obsoletos (Princípio VI - Simplicidade)
- **Decisão**: Eliminar os botões `Resetar` e `Limpar Máscaras`, bem como o rótulo `Cortar (Preview)` e a classe gráfica `CropBoxItem`.
- **Justificativa**: O `Ctrl+Z` é o mecanismo canônico de reversão. Sem caixas fixas nem máscaras acumuladas, a interface torna-se mais simples e declarativa.

## Risks / Trade-offs

- **[Consumo de RAM na Pilha de Desfazer]** $\rightarrow$ *Mitigação*: Como as imagens são codificadas em WebP com qualidade otimizada através de `comprimir_imagem_para_bytes_webp`, cada passo na pilha consome tipicamente entre 100 KB e 350 KB, permitindo centenas de passos de Undo com impacto desprezível na memória RAM.
- **[Cliques Acidentais no Modo Cortar]** $\rightarrow$ *Mitigação*: Seleções com largura ou altura menores que 10 pixels são desconsideradas, cancelando a operação sem alterar a imagem.
- **[Alternância de Imagens Durante Edição]** $\rightarrow$ *Mitigação*: Trocar de imagem na barra lateral desativa qualquer modo de seleção ativo e restaura o visualizador em estado limpo.
