## Context

O Editor Aresta é uma aplicação desktop desenvolvida em Python e PyQt6, empacotada como executável para Windows (`--windowed`) e distribuída como executável standalone ou pacote MSIX. Quando ocorrem exceções não tratadas no loop de eventos do Qt ou em threads em segundo plano, o processo encerra sem aviso e sem gerar registros acessíveis para o usuário ou para a equipe de desenvolvimento.

Além disso, as operações de edição manipulam modelos Protobuf em memória através de comandos `QUndoCommand`. Caso o aplicativo seja fechado abruptamente antes de um salvamento explícito, o trabalho em andamento é perdido e a pilha de histórico é reiniciada.

A política de privacidade do editor reside no repositório do site público em `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md` e precisa ser atualizada para refletir com transparência a telemetria técnica de falhas.

## Goals / Non-Goals

**Goals:**
- Implementar biblioteca de telemetria silenciosa de falhas via Sentry SDK (`editor/core/telemetria.py`) capturando exceções globais (`sys.excepthook`, `threading.excepthook`) e rastreamento de breadcrumbs.
- Sanitizar automaticamente dados sensíveis (substituindo caminhos de usuários do Windows por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%` e expurgando tokens/credenciais) no callback `before_send`.
- Criar biblioteca utilitária (`editor/core/imagem_anonimizada.py`) para gerar imagens WebP homogêneas preservando as dimensões originais (`largura` x `altura`) com pixels homogêneos, reduzindo fotografias para < 150 bytes durante a serialização anonimizada (`anonimizado=True`).
- Rastrear a ancestralidade da edição adicionando o campo `commit_base_sha` no protobuf `CroquiExperimental`.
- Implementar métodos `serializar(anonimizado: bool = False)` e `deserializar(dados: dict, model: CroquiModel)` para todos os comandos de histórico (`QUndoCommand`).
- Criar biblioteca de diário transacional em disco (`editor/core/diario.py` / `GerenciadorDiario`) com arquivos binários append-only (`diario_salvo.bin` e `diario_pendente.bin`) usando `pickle`.
- Prover fluxo visual de recuperação de desastres (`editor/views/dialogo_recuperacao_sessao.py`) no boot do editor quando `diario_pendente.bin` contiver dados não salvos, permitindo ao usuário recuperar as ações ou descartá-las.
- Substituir chamadas a `print(...)` pela biblioteca `editor/core/registro_log.py`, integrando `logging` estruturado ao Sentry e a arquivo de log local rotativo (`%APPDATA%/editor_aresta/logs/editor.log`).
- Atualizar a Política de Privacidade do Editor em `../arestaclimb.com/public/docs/politica-de-privacidade-editor.md`.
- Assegurar 100% de cobertura de testes unitários com TDD e testes de integração em primeiro lugar, estritamente em português brasileiro conforme `PRINCIPIOS.md`.

**Non-Goals:**
- Gravar vídeo ou capturar a tela da máquina do usuário.
- Enviar imagens completas em alta resolução para os servidores de telemetria externos.
- Sincronizar diários entre múltiplos computadores via nuvem fora do controle de versão oficial do Git.

## Decisions

### 1. Biblioteca de Telemetria (`editor/core/telemetria.py`)
- **Decisão**: Criar biblioteca independente para inicialização do `sentry-sdk` configurado com `traces_sample_rate=1.0`, `send_default_pii=True` e `enable_logs=True`, ativada no ponto de entrada `editor/main.py`.
- **Alternativas consideradas**:
  - *Webhook direto de terceiros*: Descartado por expor segredos no cliente e não prover agregação de eventos nem trilha de breadcrumbs.
  - *Windows Error Reporting nativo*: Descartado por não mapear o stack trace em nível de arquivo Python e linha de código.
- **Racional**: Biblioteca autossuficiente e testável com mocks, que consolida erros repetidos, gera alertas instantâneos e agrupa breadcrumbs das ações do usuário.

### 2. Sanitização Rigorosa e WebP Anonimizado (`editor/core/imagem_anonimizada.py`)
- **Decisão**: No hook `before_send(event, hint)`, aplicar expressões regulares para substituir caminhos absolutos locais por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%`, além de expurgar tokens do GitHub. Para imagens enviadas em anexos de diagnóstico, converter para WebP homogêneo via `gerar_webp_anonimizado()`.
- **Racional**: Garante conformidade com LGPD/GDPR e mantém o payload de upload ínfimo (< 30 KB), sem expor fotos pessoais dos usuários.

### 3. Diário Transacional com Separação Salvo vs Pendente (`editor/core/diario.py`)
- **Decisão**: Dividir a persistência local do histórico em dois arquivos binários dentro da pasta do croqui experimental:
  1. `diario_pendente.bin`: Gravação append-only com `pickle.dump(cmd_dict, f)` a cada comando despachado na `QUndoStack`.
  2. `diario_salvo.bin`: Comandos consolidados. No momento do salvamento do croqui (build/commit local), o conteúdo de `diario_pendente.bin` é concatenado ao final de `diario_salvo.bin` e `diario_pendente.bin` é truncado para 0 bytes.
- **Racional**: Permite que, em caso de crash, o editor saiba exatamente quais comandos foram executados após o último salvamento. Se o usuário escolher descartar alterações não salvas, basta limpar o arquivo pendente.

### 4. Formato de Serialização com `pickle` em Modo Append (`"ab"`)
- **Decisão**: Utilizar dicionários puros serializados via `pickle` em modo streaming binário. Cada comando de `editor/commands/` implementa `serializar(anonimizado=False)` retornando um dicionário com identificador de classe, parâmetros primitivos, caminhos no protobuf e bytes (ou dummy se `anonimizado=True`).
- **Alternativas consideradas**:
  - *JSON textual*: Exigiria codificação Base64 para arrays de bytes de imagens e parsing textual mais lento.
  - *SQLite local*: Overhead desnecessário para uma fila sequencial append-only.
- **Racional**: `pickle` oferece velocidade de microssegundos em C nativo, serialização direta de tipos `bytes` e formato binário compacto.

### 5. Rastreamento de Commit Base (`commit_base_sha`)
- **Decisão**: Incluir `string commit_base_sha = 9` em `CroquiExperimental`. Ao clonar ou instanciar um croqui experimental a partir de um oficial, o SHA atual do branch base em `aresta_db` é gravado no metadado.
- **Racional**: Permite reproduzir 100% dos bugs em ambiente de desenvolvimento rodando os comandos do diário sobre o commit base exato em que o usuário estava trabalhando.

### 6. Logging Estruturado Centralizado (`editor/core/registro_log.py`)
- **Decisão**: Implementar `editor/core/registro_log.py` com configuração de logger centralizado que direciona mensagens para a saída padrão (em desenvolvimento), para `%APPDATA%/editor_aresta/logs/editor.log` (com rotação) e para os breadcrumbs do Sentry.
- **Racional**: Elimina saídas perdidas em `--windowed` e enriquece os relatórios de crash com os eventos cronológicos precedentes.

## Risks / Trade-offs

- **[Risco] Corrupção de arquivo de diário em desligamento abrupto de energia** → *Mitigação*: Leitura com bloco `try/except EOFError` iterativo no `pickle.load`. Se o último comando foi gravado pela metade, os comandos válidos anteriores são lidos normalmente e o último bloco parcial é descartado com segurança.
- **[Risco] Cota de eventos/profiler no plano gratuito do Sentry** → *Mitigação*: A telemetria de crashes envia eventos apenas sob exceções. O profiler pode ser controlado por amostragem segura.
- **[Risco] Vazamento de dados em caminhos customizados fora do padrão Windows** → *Mitigação*: Regex genérico baseado no diretório base do usuário (`Path.home()`) e substituição universal de substrings correspondentes a nomes de login do sistema.
