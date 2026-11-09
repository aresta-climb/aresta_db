# Design

## Context

O servidor MCP do Editor Aresta (`editor/mcp/ferramentas_comandos.py`) expõe ferramentas mapeadas diretamente aos métodos de `CroquiController` e `MapasController`, garantindo que toda mutação passe pela pilha `QUndoStack` (`historico`) e pelo diário transacional (`AGENTS.md`, Princípio VIII). Atualmente:
- `aresta_migrar_setor` permite mover um `Setor` entre um `Pico` e um `Grupo`, mas não há equivalente para mover uma `Escalada` entre dois `Setor`es preservando seu `uid` e imagens em RAM.
- `aresta_alterar_campo` aceita um dicionário `campos` para alterar múltiplos campos de **um mesmo `alvo`**, mas alterações distribuídas em dezenas de `UID`s distintos (como atualizar 22 graduações, 10 nomes e dezenas de conquistadores na Gruta da Lapinha) exigem dezenas de chamadas JSON-RPC individuais.

Consulte `proposal.md` para a motivação completa e o escopo das alterações de dados na Gruta da Lapinha.

## Goals / Non-Goals

**Goals:**
- Implementar `CroquiController.migrar_escalada` e a ferramenta MCP `aresta_migrar_escalada` compondo `CmdRemoverRepeated` e `CmdAdicionarRepeated` em um `CmdMacro`, com resolução automática do setor e índice de origem a partir do `alvo_escalada`.
- Implementar `CroquiController.alterar_em_lote` e a ferramenta MCP `aresta_alterar_em_lote` permitindo mutações atômicas em múltiplos alvos com validação *fail-fast* integral antes do empilhamento na `QUndoStack`.
- Manter 100% de cobertura de testes comportamentais (`croqui_controller_test.py` e `ferramentas_comandos_test.py`) seguindo o ciclo TDD (*Red-Green-Refactor*) e sem uso de mocks internos.
- Executar 100% das correções catalogadas da Gruta da Lapinha (`br_mg_lagoa_santa_gruta_da_lapinha`) via servidor MCP do Editor Aresta.

**Non-Goals:**
- Criar novas subclasses folha de `ComandoEditor` fora dos 6 comandos canônicos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`).
- Expor ferramentas manuais de macro (`iniciar_macro`/`finalizar_macro`) no protocolo MCP.

## Decisions

### 1. Resolução Automática de Origem e Preservação de Imagens em `migrar_escalada`
- **Decisão**: `aresta_migrar_escalada` receberá `alvo_escalada` (UID ou caminho da `Escalada`), `alvo_setor_destino` (UID ou caminho do `Setor` de destino) e `indice_destino` opcional (padrão `-1`, inserindo ao final de `setor_destino.escaladas`). A partir da mensagem `Escalada` resolvida na árvore viva, o sistema obtém seu caminho canônico via `resolver_caminho_mensagem` (ex.: `picos.0.setores_ou_grupos.7.setor.conteudo.escaladas.4`), extraindo o caminho do `Setor` pai de origem e o `indice_origem` inteiro. No `CroquiController.migrar_escalada(setor_origem, indice_origem, setor_destino, indice_destino=None)`:
  1. Valida que `setor_origem` e `setor_destino` são mensagens `Setor` pertencentes à árvore ativa e que `indice_origem` está dentro dos limites de `setor_origem.escaladas`.
  2. Cria uma cópia profunda de `setor_origem.escaladas[indice_origem]` preservando o `uid` da `Escalada` e de todas as suas submensagens.
  3. Instancia `CmdRemoverRepeated(model, alvo=setor_origem, campo_nome="escaladas", index=indice_origem, valor_removido=item_origem)` e remove de `cmd_remover.imagens_removidas_ram` quaisquer caminhos de imagem presentes na `Escalada` migrada (pois continuarão referenciados no destino).
  4. Instancia `CmdAdicionarRepeated(model, alvo=setor_destino, campo_nome="escaladas", index=idx_final, valor=item_copia)` e empilha `CmdMacro([cmd_remover, cmd_adicionar], texto="Migrar Escalada")`.
- **Alternativa considerada**: Exigir que o agente informe manualmente `alvo_setor_origem` e `indice_origem` como em `aresta_migrar_setor`. Descartada como obrigatória porque toda `Escalada` possui `uid` indexado em `IndiceUidsModel`, tornando trivial e menos propenso a erro descobrir automaticamente o setor e o índice de origem (embora o método do controller receba explicitamente `setor_origem`, `indice_origem`, `setor_destino`, `indice_destino`).

### 2. Construção e Validação *Fail-Fast* em `alterar_em_lote`
- **Decisão**: Extrair no `CroquiController` o método auxiliar `_construir_comandos_para_alvo(alvo, mapa_campos, pode_mesclar, session_id) -> list[ComandoEditor]`, reutilizado tanto por `alterar_campo` quanto por `alterar_em_lote(operacoes, texto_macro="Alterar em lote")`.
  - Na camada MCP (`ferramentas_comandos.py`), `aresta_alterar_em_lote` recebe `operacoes: list[dict[str, Any]]`, onde cada item contém `alvo` e `campo`+`valor` ou `campos`.
  - Para cada item de `operacoes`, a ferramenta resolve o alvo via `resolver_alvo_mcp` e coage cada valor via `_coagir_valor_para_campo` **antes** de invocar `croqui_controller.alterar_em_lote(...)`.
  - `croqui_controller.alterar_em_lote` constrói todos os comandos folha de todos os alvos em uma única lista `comandos` (disparando `ValueError`/`TypeError` na instanciação caso qualquer alvo/campo/valor seja inválido, antes de tocar na `QUndoStack`) e, ao final, despacha um único `CmdMacro(comandos, texto=...)` e atualiza `model.indice_uids`.
- **Alternativa considerada**: Chamar `croqui_controller.alterar_campo` em um loop dentro de `iniciar_grupo_undo`/`finalizar_grupo_undo`. Descartada porque `iniciar_grupo_undo` executa `cmd.redo()` imediatamente a cada iteração; se a 10ª operação do lote falhasse na validação, as 9 primeiras já teriam mutado o `CroquiModel` em memória. Instanciar todos os comandos antes de executar garante atomicidade real (*all-or-nothing*).

### 3. Estratégia de Revisão da Gruta da Lapinha via MCP
- **Decisão**: Executar a atualização do croqui `br_mg_lagoa_santa_gruta_da_lapinha` inteiramente via chamadas MCP ao Editor Aresta seguindo 6 etapas lógicas:
  1. **Migração entre setores e criação de vias/POIs faltantes**:
     - Usar `aresta_migrar_escalada` para mover *Meio Cubanos* (`L69C6jL7Bphv5T`) do `Setor Mapa 8` (`9q7X3n9z5f2v8K`) para o `Setor Mapa 6` (`XbyH3O3b3Y0i8I`).
     - Usar `aresta_renderizar_mapa` no `Mapa` do Setor 6 (`XbyH3O3b3Y0i8I.mapas.0`) e Setor 9 (`1xK8m2P9v4L7nQ.mapas.0`) para localizar as coordenadas exatas dos círculos `61`, `132` (à direita da `63`) e `122`, adicionando os POIs e as novas escaladas `Via sem informação` (`63`, `93` e `122`) via `aresta_adicionar_repeated`.
  2. **Revinculação de referências invertidas/deslocadas**:
     - Corrigir as referências (`Mapa.Referencia`) dos POIs `44`/`45` (Mapas 3 e 4), `50`/`51` (Mapa 4), `61`/`62`/`63`/`132` (Mapa 6), `92`/`93` (Mapa 8) e `122` (Mapa 9).
  3. **Conversão de variante `oneof` (Tipo de Proteção)**:
     - Converter a via `60` (*Compromisso Sexual*, `RnZKGhZfGOypo1` no Setor 5) de `via_esportiva` para `via_movel` preservando todos os seus campos (`nome`, `dificuldade`, `extensao`, `data_abertura`, `conquistadores`, `descricao`).
  4. **Lote de Nomes, Datas de Abertura e Graduações (`aresta_alterar_em_lote`)**:
     - Aplicar em um único lote atômico todas as atualizações de `nome`, `data_abertura` (`08`, `09`, `61`, `90`) e as 22 correções de `dificuldade` (incluindo `PROJETO` nas vias `06`, `108`, `129` e mapeamento `< 7º`: `'b'` -> `_BARRA_`, `'c'` -> `SUP`).
  5. **Lote de Conquistadores e Textos/Descrições (`aresta_alterar_em_lote`)**:
     - Atualizar os conquistadores padronizados no formato `<Nome Completo> "<Apelido>"` (incluindo `Fábio Luiz Faria "Fabinho"` sem `s` nas vias `59` e `87` e co-conquistadores preservados do PDF Rumos nas vias `35`, `55` e `96`), adicionar o texto introdutório e alerta ambiental da pág. 27 em `mapas_gerais.md` e corrigir a grafia `"Vía"` -> `"Via"` nas vias `124` e `125`.
  6. **Validação e Salvamento**:
     - Executar `aresta_compilar` garantindo zero erros/avisos e persistir no disco com `aresta_salvar`.

## Risks / Trade-offs

- **[Risco] Operações no mesmo lote alterando a mesma coleção `repeated` e deslocando índices** → **Mitigação**: Em `alterar_em_lote`, quando múltiplas operações têm alvos independentes (ex.: `UID`s de diferentes `Escalada`s ou `Setor`es), todas as instâncias de comando são validadas previamente e executadas em sequência dentro do `CmdMacro`. Documentar na descrição da ferramenta que cada alvo do lote deve ser referenciado preferencialmente por seu `UID` NanoID estável.
- **[Risco] Migração de escalada dentro do mesmo setor (`setor_origem == setor_destino`)** → **Mitigação**: Se `setor_origem is setor_destino`, ajustar o índice ou delegar para `mover_repeated_para_posicao` / validar limites para que `CmdRemoverRepeated` seguido de `CmdAdicionarRepeated` mantenha o índice consistente.
