# Design

## Context

Conforme detalhado em `proposal.md` (*Why*), o Editor Aresta carece de uma visão inicial orientada a objetivos que guie o autor desde a criação de um rascunho até um croqui de excelência pronto para publicação, e o `indice.binarypb` carece de um sinal numérico de qualidade (`nota_qualidade`) para auxiliar na ordenação de croquis no aplicativo móvel.

Atualmente:
- A `JanelaPrincipal` (`editor/legacy_views/area_principal.py`) inicializa um `QStackedWidget` onde o índice `0` é `PaginaDados`, seguido de `PaginaImagens` (`1`), `PaginaMapas` (`2`), `PaginaBetas` (`3`) e `PaginaHistorico` (`4`).
- O roteamento de foco profundo entre abas já está consolidado por meio de `ContextoUIPath` (`editor/core/contexto.py`) e do sinal `foco_requisitado` conectado a `_on_foco_requisitado` na `JanelaPrincipal`.
- O script `scripts/deploy_generated.py` compila cada croqui e popula `PrecomputadosResumoCroqui` em `indice.binarypb` e `indice.yaml`, enquanto `scripts/medir_saude_croquis.py` avalia indicadores de saúde para gerar `STATUS_CROQUIS.md`.

## Goals / Non-Goals

**Goals:**
- Desenvolver toda a solução de forma **100% desacoplada da `JanelaPrincipal` (`editor/legacy_views/area_principal.py`)** durante as etapas de construção (motor `avaliador_nota_qualidade`, integração no pipeline de deploy/saúde e componente visual autônomo `WidgetPainelQualidade`), realizando o acoplamento na `JanelaPrincipal` exclusivamente como última etapa para permitir desenvolvimento paralelo sem conflitos.
- Fornecer uma biblioteca pura, desacoplada de GUI e testável isoladamente (`editor/core/avaliador_nota_qualidade.py`) que avalie tanto uma instância Protobuf `Croqui` (em tempo real no Editor) quanto os dados compilados/dicionários no pipeline de deploy (`deploy_generated.py` e `medir_saude_croquis.py`).
- Implementar a interface `WidgetPainelQualidade` (`editor/views/widget_painel_qualidade.py`) como um widget MVC autossuficiente (que recebe `CroquiModel` e `CroquiController` e emite `foco_requisitado`), respeitando o histórico de comandos (`QUndoCommand`) para mutações em `publicar_croqui`.
- Persistir `nota_qualidade` em `PrecomputadosResumoCroqui` (`indice.proto`) sem introduzir redundância no `compilado.binarypb`.

**Non-Goals:**
- Alterar o algoritmo de ranking no código do aplicativo móvel (este repositório produz o `indice.binarypb` com o novo campo `nota_qualidade` para consumo pelo cliente).
- Bloquear no servidor ou no botão "Propor Mudança" o envio de Pull Requests de rascunhos em progresso (`publicar_croqui = false`).
- Incluir volume/tamanho do croqui (`total_escaladas`) dentro de `nota_qualidade`, pois o tamanho já é exposto separadamente em `PrecomputadosResumoCroqui.total_escaladas`.

## Decisions

### 1. Escala Aberta por Ordens de Grandeza (`1000` / `100` / `10`) vs. Escala Fechada (`0..100`)
- **Decisão**: Adotar uma escala aditiva aberta estruturada em três faixas de pesos por ordem de grandeza:
  - **Etapa 1 (Essenciais para Publicação)**: `1000` pontos por tarefa (7 tarefas = até `7000` pontos).
  - **Etapa 2 (Qualidade, Navegação Offline e Segurança)**: `100` pontos por tarefa (7 tarefas = até `700` pontos).
  - **Etapa 3 (Lapidação, História e Comunidade)**: `10` pontos por tarefa (7 tarefas = até `70` pontos).
- **Racional**: Uma escala fechada (`0..100`) sofre de desvalorização retroativa sempre que uma nova funcionalidade é introduzida no ecossistema Aresta (reduzindo a nota de croquis que antes estavam no máximo). Na escala aberta por ordens de grandeza, novos critérios podem ser adicionados no futuro sem penalizar notas existentes, e a separação em `1000 / 100 / 10` garante ordenação lexicográfica natural: um croqui com pendências básicas na Etapa 1 jamais ultrapassa um croqui que concluiu toda a Etapa 1 apenas acumulando itens cosméticos das Etapas 2 e 3.
- **Alternativas consideradas**: Escala percentual `0..100` (descartada pela necessidade de recalibração global de pesos a cada nova feature).

### 2. Pontuação Parcial Linear com Teto na Meta de 90% e Aplicabilidade Automática
- **Decisão**:
  - Para tarefas baseadas em cobertura percentual com meta $M = 0.90$ e peso máximo $P$, os pontos obtidos são calculados como:
    $$\text{pontos} = \min\left(P, \text{round}\left(P \times \frac{\text{cobertura\_atual}}{0.90}\right)\right)$$
    A tarefa é marcada como `concluida = True` assim que $\text{cobertura\_atual} \ge 0.90$ (ou `1.0` para tarefas binárias/estruturais de 100%).
  - **Regra de Aplicabilidade Automática**: Cada avaliador de tarefa filtra o universo de entidades aplicáveis (ex: setores quando `total_setores > 1` para Mapa Geral; vias encordadas `ViaEsportiva`, `ViaMovel` e `ViaMultiplasEnfiadas` para extensão e proteções). Se o universo aplicável for vazio (`total_aplicavel == 0`), a tarefa concede automaticamente $P$ pontos (`100%`) e `concluida = True` (desde que o croqui já possua a estrutura mínima de pelo menos 1 pico, 1 setor e 1 escalada).
- **Racional**: Em croquis grandes (50+ escaladas), o modelo "tudo ou nada" não oferece feedback visual enquanto o autor preenche os primeiros 89% das vias. A rampa linear recompensa cada via mapeada ou graduada imediatamente no painel e diferencia no `indice.binarypb` croquis quase completos de croquis vazios. A aplicabilidade automática garante justiça entre modalidades (ex: croquis exclusivos de Boulder ou falésias de setor único).

### 3. Estrutura de Dados do Avaliador (`editor/core/avaliador_nota_qualidade.py`)
- **Decisão**: Modelar o retorno de `avaliar_nota_qualidade_croqui(...)` com dataclasses imutáveis em português:
  - `AcaoTarefaQualidade`: `rotulo: str`, `uri_contexto: str` (compatível com `ContextoUIPath`, ex: `page:dados/node:Croqui/expando:picos/item:0` ou `page:mapas/file:setor_x.md`).
  - `TarefaQualidade`: `id_tarefa: str`, `titulo: str`, `descricao: str`, `etapa: int` (`1`, `2` ou `3`), `pontos_obtidos: int`, `pontos_maximos: int`, `concluida: bool`, `progresso_atual: int`, `progresso_total: int`, `acoes: tuple[AcaoTarefaQualidade, ...]`.
  - `ResumoEtapaQualidade`: `numero_etapa: int`, `titulo: str`, `pontos_obtidos: int`, `pontos_maximos: int`, `tarefas_concluidas: int`, `total_tarefas: int`, `concluida: bool`, `tarefas: tuple[TarefaQualidade, ...]`.
  - `ResultadoNotaQualidade`: `nota_qualidade: int`, `nota_maxima: int`, `pronto_para_publicar: bool` (`etapa_1.concluida`), `publicado: bool`, `etapas: tuple[ResumoEtapaQualidade, ...]`.
- **Racional**: Permite que tanto a View (`WidgetPainelQualidade`) quanto os scripts de linha de comando (`deploy_generated.py` e `medir_saude_croquis.py`) consumam exatamente o mesmo motor sem acoplamento com `PySide6`.

### 4. Construção Desacoplada do `WidgetPainelQualidade` e Acoplamento Tardio na `JanelaPrincipal`
- **Decisão**:
  - Desenvolver e testar `WidgetPainelQualidade` (`editor/views/widget_painel_qualidade.py`) de forma completamente independente da `JanelaPrincipal`. O widget recebe apenas `model: CroquiModel` e `controller: CroquiController`, escuta os sinais do `CroquiModel` para se atualizar, despacha alterações de `publicar_croqui` via `controller.editar_campo(...)` (pilha de Undo/Redo) e solicita navegação emitindo `model.requisitar_foco(uri)` (ou sinal próprio `foco_requisitado`).
  - Somente na última fase de implementação (após Protobuf, motor de avaliação, scripts de deploy/saúde e `WidgetPainelQualidade` estarem 100% prontos e testados isoladamente), realizar o acoplamento em `editor/legacy_views/area_principal.py`, inserindo `PaginaPainel` no índice `0` do `QStackedWidget` e na barra lateral (`acao_nav_painel`).
- **Racional**: Evita conflitos de merge em `area_principal.py` e evita quebrar testes existentes da `JanelaPrincipal` enquanto o trabalho paralelo ocorre no editor.

## Risks / Trade-offs

- **[Risk] Conflitos ou quebra de índices no `QStackedWidget` durante desenvolvimento paralelo na `JanelaPrincipal`** → **Mitigation**: Manter `editor/legacy_views/area_principal.py` intocado durante toda a construção dos Grupos 1 a 4; o acoplamento na `JanelaPrincipal` é isolado no Grupo 5 final.
- **[Risk] Custo de recálculo da nota a cada tecla digitada na aba Dados** → **Mitigation**: O cálculo em memória sobre o objeto Protobuf `Croqui` é $O(N)$ onde $N$ é o número de escaladas/setores (tipicamente $< 200$, levando $< 1\text{ ms}$), e na UI do Painel a atualização visual completa só precisa ocorrer quando o `WidgetPainelQualidade` está visível ou quando sinais estruturais/de campo são emitidos pelo `CroquiModel`.

## Migration Plan

1. **Fase 1 (Protobuf — Isolada)**: Adicionar `PROJETO` ao enum `GrauBoulder` em `aresta_api/proto/croqui.proto` e `int32 nota_qualidade = 10;` em `PrecomputadosResumoCroqui` em `aresta_api/proto/indice.proto`, regerando os stubs com `python build.py protos -f`.
2. **Fase 2 (Core Library — Isolada)**: Implementar `editor/core/avaliador_nota_qualidade.py` com 100% de cobertura comportamental em `editor/core/avaliador_nota_qualidade_test.py`.
3. **Fase 3 (Pipeline de Compilação e Saúde — Isolada da UI)**: Integrar o cálculo de `nota_qualidade` em `scripts/deploy_generated.py` e `scripts/medir_saude_croquis.py` (com seus respectivos testes).
4. **Fase 4 (View Autônoma — Isolada da `JanelaPrincipal`)**: Adicionar o ícone em `editor/views/estilo.py` e implementar `editor/views/widget_painel_qualidade.py` (e `widget_painel_qualidade_test.py`) testado diretamente contra `CroquiModel` e `CroquiController`, sem tocar em `area_principal.py`.
5. **Fase 5 (Acoplamento Final na `JanelaPrincipal`)**: Conectar `PaginaPainel` como aba primária (índice `0`) em `editor/legacy_views/area_principal.py`, ajustar os testes da janela principal e executar `python build.py tudo`.
