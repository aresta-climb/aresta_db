# Spec Delta

## Purpose

Prover uma infraestrutura determinística de testes exploratórios caóticos de interface gráfica (PySide6/Qt) e fuzzing de entradas para o Editor Aresta, capaz de exercitar toda a aplicação offline, auditar invariantes de estado e histórico, encolher falhas por busca binária (`ddmin`) e manter uma suíte contínua de regressão de crashes.

## ADDED Requirements

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
A cada passo executado, o motor SHALL verificar três oráculos independentes: ausência de exceções não tratadas ou objetos C++ deletados, simetria determinística do estado Protobuf na pilha de `Undo`/`Redo` e integridade estrutural do diário binário de sessão.

#### Scenario: Detecção de exceção em slot Qt ou objeto C++ já deletado
- **WHEN** um slot Qt, temporizador ou thread em segundo plano lança uma exceção não tratada (como `RuntimeError: Internal C++ object already deleted`)
- **THEN** o oráculo de exceções SHALL capturar imediatamente o erro e seu stacktrace, interrompendo a semente atual e registrando a falha.

#### Scenario: Detecção de quebra de simetria na pilha de Undo/Redo
- **WHEN** o motor executa `Undo` ou `Redo` para um índice da pilha de histórico previamente visitado (sem salvamento modificador intermediário) e a serialização determinística do Protobuf diverge do hash registrado naquele índice
- **THEN** o oráculo de simetria SHALL reportar uma falha de corrupção de estado ou mutação fora de comando de histórico.

#### Scenario: Verificação de integridade do diário transacional
- **WHEN** comandos são gravados no diário pendente ou consolidados no diário salvo durante a sessão
- **THEN** o oráculo de diário SHALL validar que os arquivos binários do diário permanecem legíveis e desserializáveis sem erro.

### Requirement: Bloqueio Hard de Rede Externa Durante os Testes
O sistema SHALL bloquear qualquer tentativa de conexão de rede externa (fora de loopback `127.0.0.1`, `::1` ou `localhost`) ou abertura de navegador externo do sistema operacional durante a execução das sementes do robô caótico.

#### Scenario: Tentativa acidental de conexão externa durante um passo
- **WHEN** qualquer componente tenta abrir um socket TCP/UDP para um endereço externo (ex: `8.8.8.8`, `github.com` ou `previa.arestaclimb.com`) durante a exploração
- **THEN** o guardião de rede SHALL impedir a conexão e lançar imediatamente `ErroAcessoRedeProibidoEmTeste`, fazendo o teste falhar com diagnóstico explícito.

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
O sistema SHALL prover um teste de regressão que reexecute todos os arquivos JSON em `editor/caos/caminhos_regressao/` e um executor de campanha por orçamento de tempo que rode sementes continuamente, deduplique falhas pela assinatura e consolide o resultado.

#### Scenario: Execução automática de receitas de regressão salvas
- **WHEN** a suíte de testes automatizados é executada
- **THEN** todos os arquivos `.json` presentes em `editor/caos/caminhos_regressao/` SHALL ser carregados e reproduzidos sem falhas.

#### Scenario: Deduplicação de falhas idênticas durante campanha por tempo
- **WHEN** duas sementes diferentes encontram exatamente a mesma assinatura (`tipo_excecao + frame_principal`) durante uma campanha por orçamento de tempo
- **THEN** o motor SHALL executar o encolhimento e o envio ao Sentry apenas na primeira ocorrência, incrementando o contador de ocorrências nas seguintes para preservar o orçamento de tempo.
