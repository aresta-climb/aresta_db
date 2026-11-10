# Proposal

## Why

Atualmente, os botões de ação rápida do Painel de Qualidade do Croqui exibem rótulos genéricos prefixados com `"Ir para: Editar..."` e navegam apenas para o topo do nó na árvore da aba "Dados", sem posicionar o scroll nem dar foco no campo específico que precisa ser preenchido — deixando o usuário perdido especialmente em formulários longos ou quando o campo pendente está recolhido dentro de "Opções Avançadas". Tornar cada botão direto ao ponto (ex: `"Adicionar localização"`, `"Adicionar link Google Maps"`) e levá-lo exatamente até o campo alvo com scroll e foco (incluindo expansão automática da seção avançada) reduz drasticamente o atrito para elevar a nota de qualidade do croqui.

## What Changes

- **Extensão do protocolo `ContextoUIPath` com sufixo `/campo:<nome_campo>`**:
  - Suportar o segmento opcional `/campo:<nome_campo>` ao final de URIs de contexto (ex: `page:dados/node:root/node:Croqui/expando:picos/item:0/campo:url_google_maps`).
  - Expor a propriedade `campo_alvo` em `ContextoUIPath` mantendo `caminho_local_arvore` limpo (sem o sufixo `/campo:...`) para que a resolução de nós na árvore continue operando sem alterações.
- **Scroll, foco e auto-expansão de Opções Avançadas em `WidgetEditorDados` e `WidgetFormularioPadrao`**:
  - Garantir que `_on_foco_requisitado` em `WidgetEditorDados` processe o foco no `campo_alvo` mesmo quando o nó da árvore já estiver selecionado.
  - Implementar `focar_campo(nome_campo)` em `WidgetFormularioPadrao`: caso o campo pertença à seção colapsável `WidgetSecaoAvancada` (`(aresta.avancado) = true`), expandi-la automaticamente antes de rolar; posicionar o `QScrollArea` do formulário para deixar o card/container do campo visível (`ensureWidgetVisible`) e acionar `setFocus()` no controle interativo principal do campo (ou botão de ação correspondente).
- **Remoção do prefixo `"Ir para: "` e revisão das 22 tarefas do Painel de Qualidade**:
  - Remover o prefixo fixo `"Ir para: "` de `CardTarefaQualidade.atualizar_tarefa`, exibindo diretamente o `acao.rotulo`.
  - Revisar todas as 22 tarefas das Etapas 1, 2 e 3 em `avaliador_nota_qualidade.py` para gerar ações granulares por campo pendente com rótulos imperativos diretos (ex: `"Adicionar localização"`, `"Adicionar link Google Maps"`, `"Gerar mapa de pontos"`, `"Adicionar estacionamento (<Setor>)"`, `"Adicionar localização da parede (<Setor>)"`, `"Marcar revisão manual"`, `"Marcar revisão de bounding circle"`).
  - Omitir o sufixo `(<Nome do Pico>)` nos rótulos de ações de tarefas de pico quando o croqui possuir apenas 1 pico, exibindo-o quando houver 2 ou mais picos.
  - Na tarefa **2.5 (Escaladas de destaque nos setores)**, direcionar a ação para a primeira escalada do setor focando no campo `destaque` (`.../expando:escaladas/item:0/campo:destaque`) e expandindo o nó `Escaladas` na árvore lateral.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida. -->

### Modified Capabilities
- `painel-nota-qualidade-croqui`: Atualiza o requisito de ações rápidas de navegação direta por tarefa para exigir rótulos diretos sem prefixo `"Ir para: "`, desmembramento por campo pendente com sufixo `/campo:<nome_campo>`, omissão do nome do pico em croquis de pico único e navegação direta ao campo `destaque` da primeira escalada do setor.
- `editor-dados-formularios`: Adiciona o requisito de navegação direta, auto-expansão de seção avançada, scroll e foco em campo específico do formulário via `ContextoUIPath` (`/campo:<nome_campo>`).

## Impact

- `editor/core/contexto.py` e `editor/core/contexto_test.py`: Parsing e exposição de `campo_alvo` para o sufixo `/campo:<nome_campo>`.
- `editor/core/avaliador_nota_qualidade.py` e `editor/core/avaliador_nota_qualidade_test.py`: Revisão dos rótulos e URIs (`AcaoTarefaQualidade`) nas 22 tarefas das Etapas 1, 2 e 3.
- `editor/views/widget_painel_qualidade.py` e `editor/views/widget_painel_qualidade_test.py`: Remoção do prefixo `"Ir para: "` nos botões de `CardTarefaQualidade`.
- `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_dados_test.py`: Implementação de `focar_campo` com auto-expansão de `WidgetSecaoAvancada`, scroll no `QScrollArea` e foco no widget do campo alvo.
