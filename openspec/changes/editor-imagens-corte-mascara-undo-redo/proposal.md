## Why

Atualmente, no Editor de Imagens (`WidgetEditorImagens`), as operações de rotação (90° horária e anti-horária), corte e aplicação de máscaras operam diretamente em objetos de imagem locais (`PageState`) sem emitir comandos para a pilha global de histórico (`QUndoStack` / `GerenciadorHistorico` / `CmdSubstituirImagemMemoria`). Isso viola o **Princípio VII (Edições de Estado via Comandos do Histórico)**, impede o uso de Desfazer/Refazer (`Ctrl+Z` / `Ctrl+Y`), quebra a persistência no diário de recuperação contra falhas (`diario_pendente.bin`) e viola o **Princípio II (Library-First)** ao acoplar lógica de manipulação de pixels diretamente no interior de componentes gráficos da interface com o usuário.

Além disso, a ferramenta de corte atual depende de uma caixa vermelha permanente sobre a imagem (`CropBoxItem`) que atua como pré-visualização fixa e polui a cena gráfica. A experiência requer um "Modo Cortar" interativo por seleção direta (arrastar retângulos na tela com corte imediato ao soltar o mouse), acompanhado por um fluxo direto de máscaras (conta-gotas + seleção retangular imediata). Com o suporte integral a Desfazer/Refazer em todas as ações, botões paliativos como "Resetar" e "Limpar Máscaras" tornam-se obsoletos e devem ser removidos.

## What Changes

- **Biblioteca Pura de Transformações de Imagem (Princípio II - Library-First)**:
  - Criação do módulo desacoplado `editor/core/transformacoes_imagem.py` (com `transformacoes_imagem_test.py`), contendo funções puras de manipulação de bytes WebP (`rotacionar_imagem_bytes`, `cortar_imagem_bytes`, `aplicar_mascara_bytes` e `obter_cor_pixel`).
- **Integração Total com Desfazer/Refazer (Princípio VII - Comandos do Histórico)**:
  - Rotação, corte e aplicação de máscara passam a ser despachados via `CroquiController.substituir_imagem`, empilhando `CmdSubstituirImagemMemoria` no `GerenciadorHistorico`.
- **Modo Cortar Interativo por Seleção Direta**:
  - O botão "✂ Cortar" ativa o modo de seleção com cursor em formato de mira.
  - O usuário clica e arrasta para demarcar a área desejada (com retângulo de seleção elástico).
  - Ao soltar o mouse, a imagem é cortada imediatamente e o comando é empilhado no histórico (permitindo desfazer com `Ctrl+Z`).
  - Cancelamento transparente via tecla `Esc` ou novo clique no botão "Cortar".
- **Modo Máscara Direto (Conta-gotas + Retângulo)**:
  - O usuário ativa a ferramenta de máscara, clica na imagem para capturar a cor de fundo (conta-gotas) e arrasta um retângulo sobre a área a ser ocultada.
  - Ao soltar o mouse, a área é preenchida na imagem em memória RAM e registrada como um passo atômico de Desfazer/Refazer.
- **Limpeza de Interface e Remoção de Controles Obsoletos**:
  - Remoção dos botões "Resetar" e "Limpar Máscaras".
  - Remoção da caixa vermelha persistente de corte (`CropBoxItem`).
  - Remoção do texto "Cortar (Preview)" em favor de "Cortar".
- **Conformidade com os Princípios de Engenharia Aresta**:
  - Todo o código, funções, variáveis, testes e documentações 100% em português brasileiro (**Princípio I**).
  - Testes de integração em primeiro lugar (**Princípio V**).
  - Desenvolvimento orientado a testes TDD Vermelho-Verde-Refatorar (**Princípio IV**).
  - 100% de cobertura de testes unitários (**Princípio III**).

## Capabilities

### Modified Capabilities
- `editor-imagens`: Integração de todas as ações de edição (rotação, corte por seleção e máscara direta) com o sistema de `QUndoCommand` (`CmdSubstituirImagemMemoria`) através de biblioteca pura desacoplada, remoção de controles obsoletos de reset/limpeza e adoção do modo de seleção por arrasto para corte e máscaras.

## Impact

- **Código Afetado**:
  - `editor/core/transformacoes_imagem.py` [NOVO]: Biblioteca pura de transformações de imagem.
  - `editor/core/transformacoes_imagem_test.py` [NOVO]: Testes unitários com 100% de cobertura para a biblioteca de transformações.
  - `editor/legacy_views/widget_editor_imagens.py`: Refatoração para utilizar a biblioteca pura e despachar comandos para o `CroquiController`, remoção de itens estáticos e botões obsoletos.
  - `editor/legacy_views/widget_editor_imagens_test.py` e `editor/legacy_views/area_principal_imagens_integracao_test.py`: Atualização e expansão da cobertura de testes unitários e de integração.
- **APIs / Dados**:
  - Nenhuma alteração no esquema Protobuf.
  - Utiliza `CmdSubstituirImagemMemoria` existente para manter compatibilidade com o diário e o salvamento em disco.
