# robo-caotico-editor-aresta Specification

## Purpose
Prover uma infraestrutura determinística de testes exploratórios caóticos de interface gráfica (PySide6/Qt) e fuzzing de entradas para o Editor Aresta, capaz de exercitar toda a aplicação offline, auditar invariantes de estado e histórico, encolher falhas por busca binária (`ddmin`) e manter uma suíte contínua de regressão de crashes.

## Requirements

### Requirement: Exploração Caótica Determinística com Orçamento Ponderado
O sistema SHALL prover um motor de exploração caótica guiado por semente (`seed`) que execute ações sintéticas na interface Qt cobrindo todo o aplicativo através de um orçamento ponderado entre o fluxo de entrada e a janela principal de edição.

#### Scenario: Reprodutibilidade determinística para a mesma semente
- **WHEN** o motor de exploração é executado duas vezes sobre o mesmo dataset inicial utilizando a mesma `seed` e o mesmo número de passos
- **THEN** o motor MUST produzir exatamente a mesma sequência de passos e seletores de alvos em ambas as execuções.

#### Scenario: Distribuição de passos por orçamento ponderado
- **WHEN** uma sessão exploratória completa é iniciada a partir do fluxo do aplicativo
- **THEN** o motor SHALL dedicar a fase inicial (10% a 15% do orçamento) para atravessar as telas de abertura, autenticação, seleção ou criação de croqui e dedicar os 85% a 90% restantes às interações profundas dentro da janela principal de edição.

### Requirement: Fuzzing de Entradas em Formulários, Árvore, Imagens e Mapas
O motor SHALL sortear e aplicar ações de fuzzing sobre os componentes interativos visíveis das abas de Dados, Imagens, Mapas, Betas e barras de ferramentas, incluindo entradas de texto hostis, alternância de seletores `oneof`, manipulações na árvore Protobuf, traçados na cena gráfica 2D e rajadas de desfazer/refazer.

#### Scenario: Injeção de entradas fuzz em campos de formulário e coordenadas
- **WHEN** o motor seleciona um campo de texto, numérico ou coordenada E7 visível no formulário de dados
- **THEN** o motor SHALL injetar valores sorteados do dicionário de fuzzing (textos vazios, strings longas sem espaços, emojis compostos, delimitadores YAML/Markdown, links de referência quebrados ou coordenadas limítrofes) e confirmar a edição.

#### Scenario: Interação caótica em cena vetorial de mapas e editor de imagens
- **WHEN** a aba de Mapas ou de Imagens estiver ativa durante a exploração
- **THEN** o motor SHALL sortear cliques, arrastes de mouse, mudanças de ferramentas de desenho/corte/máscara e ajustes de controles deslizantes sobre a cena gráfica.

#### Scenario: Rajadas de desfazer e refazer intercaladas com edições
- **WHEN** a pilha de histórico possuir comandos empilhados durante a exploração
- **THEN** o motor SHALL sortear ações simples e rajadas consecutivas de `Undo` e `Redo` intercaladas com trocas de abas e salvamentos.

### Requirement: Interceptação Automática de Diálogos Modais Qt
O motor SHALL detectar automaticamente qualquer diálogo modal (`QDialog`, `QMessageBox` ou similar) aberto durante a execução de um passo, interagir com seus controles internos e encerrar o diálogo sem bloquear permanentemente o loop de eventos do teste.

#### Scenario: Desbloqueio de diálogo modal acionado por botão da interface
- **WHEN** uma ação do robô dispara a abertura de um diálogo modal bloqueante (`.exec()`)
- **THEN** o interceptador de modais SHALL identificar o widget modal ativo, executar passos de preenchimento ou seleção dentro do diálogo e acionar sua confirmação ou cancelamento para restituir o controle ao loop principal.

### Requirement: Oráculos de Exceção, Simetria de Undo/Redo e Integridade do Diário
A cada passo executado, o motor SHALL verificar três oráculos independentes: ausência de exceções não tratadas, logs de erro (`ERROR`/`CRITICAL`) ou objetos C++ deletados, simetria determinística do estado Protobuf na pilha de `Undo`/`Redo` e integridade estrutural do diário binário de sessão, garantindo que toda falha detectada possua um *traceback* real da pilha de execução no ponto da verificação.

#### Scenario: Detecção de exceção em slot Qt ou objeto C++ já deletado
- **WHEN** um slot Qt, temporizador ou thread em segundo plano lança uma exceção não tratada (como `RuntimeError: Internal C++ object already deleted`)
- **THEN** o oráculo de exceções SHALL capturar imediatamente a exceção original com seu *traceback* completo, interrompendo a semente atual e registrando a falha.

#### Scenario: Detecção de erro registrado no logger da aplicação
- **WHEN** um componente ou thread em segundo plano (como a tarefa de salvamento ou publicação) captura uma exceção internamente e emite um registro de nível `ERROR` ou `CRITICAL` no logger da aplicação
- **THEN** o oráculo SHALL interceptar o registro (extraindo `exc_info` quando presente ou levantando uma exceção real com *traceback* no ponto do log), interromper a semente atual e tratá-la como falha reproduzível para encolhimento e envio ao Sentry.

#### Scenario: Detecção de quebra de simetria na pilha de Undo/Redo
- **WHEN** o motor executa `Undo` ou `Redo` para um índice da pilha de histórico previamente visitado (sem salvamento modificador intermediário) e a serialização determinística do Protobuf diverge do hash registrado naquele índice
- **THEN** o oráculo de simetria SHALL levantar e capturar uma `AssertionError` com *traceback* completo da pilha de chamadas, reportando a falha de corrupção de estado ou mutação fora de comando de histórico.

#### Scenario: Verificação de integridade do diário transacional
- **WHEN** comandos são gravados no diário pendente ou consolidados no diário salvo durante a sessão
- **THEN** o oráculo de diário SHALL validar que os arquivos binários do diário permanecem legíveis e desserializáveis sem erro, levantando exceção com *traceback* completo caso detecte corrupção.

### Requirement: Bloqueio Hard de Rede Externa Durante os Testes
O sistema SHALL bloquear qualquer tentativa de conexão de rede externa ou abertura de navegador externo do sistema operacional durante a execução das sementes do robô caótico, exceto conexões de loopback (`127.0.0.1`, `::1`, `localhost`) e o endpoint de ingestão de telemetria do Sentry (`*.ingest.us.sentry.io` / `*.sentry.io`).

#### Scenario: Tentativa acidental de conexão externa durante um passo
- **WHEN** qualquer componente tenta abrir um socket TCP/UDP para um endereço externo não autorizado (ex: `8.8.8.8`, `github.com`, `supabase.co` ou `previa.arestaclimb.com`) durante a exploração
- **THEN** o guardião de rede SHALL impedir a conexão e lançar imediatamente `ErroAcessoRedeProibidoEmTeste`, fazendo o teste falhar com diagnóstico explícito.

#### Scenario: Permissão de tráfego de telemetria para o Sentry
- **WHEN** o SDK de telemetria resolve DNS ou abre conexão HTTPS para um host de ingestão do Sentry (`*.ingest.us.sentry.io` ou `*.sentry.io`) durante uma campanha de *fuzz testing*
- **THEN** o guardião de rede SHALL permitir a conexão sem lançar exceção de bloqueio.

### Requirement: Fábrica de Datasets Normal e Tóxico
O sistema SHALL prover uma fábrica determinística capaz de inicializar em diretório temporário tanto um dataset **Normal** (croqui realista completo) quanto um dataset **Tóxico** contendo casos extremos de estrutura Protobuf, Markdown, coordenadas e imagens.

#### Scenario: Geração de dataset tóxico de estresse
- **WHEN** a fábrica é solicitada a construir um ambiente com o perfil `toxico`
- **THEN** o ambiente gerado SHALL conter picos sem setores, grupos aninhados profundos, setores sem vias, textos longos com caracteres especiais e emojis, referências inválidas e imagens com dimensões extremas.

### Requirement: Encolhimento de Caminho de Crash por Busca Binária (`ddmin`)
Ao detectar uma falha em qualquer oráculo, o sistema SHALL executar o algoritmo *Delta Debugging* (`ddmin`) para podar iterativamente os passos até encontrar a menor sub-sequência que reproduz a mesma assinatura de falha, persistindo a receita em JSON.

#### Scenario: Redução de sequência longa para receita mínima reproduzível
- **WHEN** uma sequência de 60 passos falha no passo 60 mas apenas 3 passos são necessários para reproduzir a mesma exceção
- **THEN** o encolhedor SHALL testar partições em instâncias limpas do ambiente até isolar a sequência mínima e salvar o arquivo JSON com `passos_minimos` e `passos_originais`.

#### Scenario: Ignorar passos órfãos durante tentativa de poda
- **WHEN** uma partição intermediária testada pelo encolhedor contém um passo cujo widget alvo não está presente na tela
- **THEN** o executor de replay SHALL tratar o passo ausente como `no-op` e prosseguir até verificar se a mesma falha ocorre ao final.

### Requirement: Suíte de Regressão de Caminhos e Campanha por Tempo com Deduplicação
O sistema SHALL prover um teste de regressão que reexecute todos os arquivos JSON em `editor/caos/caminhos_regressao/`, um executor de campanha por orçamento de tempo que mantenha a telemetria ativa do início ao fim isolando os replays de poda (`ddmin`) para preservar os *breadcrumbs* da semente que falhou, e um ponto de entrada de linha de comando para execução local simplificada sem afetar a suíte unitária padrão.

#### Scenario: Execução automática de receitas de regressão salvas
- **WHEN** a suíte de testes automatizados é executada
- **THEN** todos os arquivos `.json` presentes em `editor/caos/caminhos_regressao/` SHALL ser carregados e reproduzidos sem falhas.

#### Scenario: Deduplicação de falhas idênticas durante campanha por tempo
- **WHEN** uma semente encontra uma assinatura de falha inédita durante uma campanha com envio ao Sentry ativo
- **THEN** o motor SHALL executar as reexecuções de busca binária (`ddmin`) em um escopo isolado e silencioso do Sentry (sem descartar nem sobrescrever os *breadcrumbs* e o diário acumulados nos passos da semente original), salvar o arquivo `.json` reduzido e despachar um único evento ao Sentry com os *breadcrumbs* originais, o *stacktrace* real e o `.json` anexado.

#### Scenario: Execução local via ponto de entrada de linha de comando
- **WHEN** o desenvolvedor executa o ponto de entrada de linha de comando do robô caótico sem argumentos adicionais
- **THEN** o sistema SHALL iniciar uma campanha local com janela visível por padrão, telemetria do Sentry habilitada e gravação automática de receitas `.json` em `editor/caos/caminhos_regressao/`, sem alterar o comportamento *headless* dos testes unitários do `pytest`.
