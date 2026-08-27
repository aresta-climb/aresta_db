## Context

O Editor Aresta é uma aplicação desktop desenvolvida em Python e PyQt6, empacotada como executável para Windows (`--windowed`) e distribuída como executável standalone ou pacote MSIX. Quando ocorrem exceções não tratadas no loop de eventos do Qt ou em threads em segundo plano, o processo encerra sem aviso e sem gerar registros acessíveis para o usuário ou para a equipe de desenvolvimento.

Além disso, as operações de edição manipulam modelos Protobuf em memória através de comandos `QUndoCommand`. Caso o aplicativo seja fechado abruptamente antes de um salvamento explícito, o trabalho em andamento é perdido e a pilha de histórico é reiniciada.

## Goals / Non-Goals

**Goals:**
- Implementar telemetria silenciosa de crashes via Sentry SDK com captura de exceções globais (`sys.excepthook`, `threading.excepthook`) e rastreamento de breadcrumbs.
- Sanitizar automaticamente dados sensíveis (substituindo caminhos de usuários do Windows por `%APPDATA%`, `%USERPROFILE%` e removendo tokens/credenciais) no callback `before_send`.
- Criar helper de imagem WebP dummy que preserve as dimensões originais (`width` x `height`) com pixels homogêneos, reduzindo fotos de megabytes para < 100 bytes durante a serialização redigida (`redacted=True`).
- Rastrear a ancestralidade da edição adicionando o campo `commit_base_sha` no protobuf `CroquiExperimental`.
- Implementar métodos `serializar(redacted=False)` e `deserializar(dados, model)` para todos os comandos de histórico (`QUndoCommand`).
- Criar sistema transacional de journaling em disco com arquivos binários append-only (`journal_salvo.bin` e `journal_pendente.bin`) usando `pickle`.
- Prover fluxo de recuperação de desastres (Crash Recovery) no boot do editor quando `journal_pendente.bin` contiver dados não salvos, permitindo ao usuário recuperar as ações ou descartá-las.
- Substituir chamadas a `print(...)` por `logging` estruturado integrado ao Sentry e a arquivo de log local rotativo (`%APPDATA%/editor_aresta/logs/editor.log`).
- Publicar a Política de Privacidade formal no repositório (`PRIVACIDADE.md`).

**Non-Goals:**
- Gravar gravação contínua de vídeo ou captura de tela da máquina do usuário.
- Enviar imagens completas em alta resolução para os servidores de telemetria externos.
- Sincronizar journals entre múltiplos computadores via nuvem em tempo real (fora do escopo do Git oficial).

## Decisions

### 1. Telemetria com Sentry SDK e Captura de Hooks Globais
- **Decisão**: Utilizar `sentry-sdk` configurado com `traces_sample_rate=1.0`, `send_default_pii=True` e `enable_logs=True`, inicializado no ponto de entrada mais alto do aplicativo (`editor/main.py`).
- **Alternativas consideradas**:
  - *Webhook direto do Discord/Telegram hardcoded*: Descartado por expor segredos/chaves de webhook no binário do cliente e carecer de agrupamento de erros e métricas.
  - *Windows Error Reporting nativo*: Descartado por não mapear o stack trace em nível de arquivo Python e linha de código.
- **Racional**: O Sentry consolida erros repetidos, gera alertas instantâneos e agrupa breadcrumbs das ações do usuário.

### 2. Sanitização Rigorosa via `before_send` e Helper Dummy WebP
- **Decisão**: No hook `before_send(event, hint)`, aplicar expressões regulares para substituir caminhos absolutos locais por `%APPDATA%`, `%LOCALAPPDATA%` ou `%USERPROFILE%`, além de expurgar tokens do GitHub. Para imagens enviadas em anexos de telemetria, converter para WebP homogêneo via `gerar_dummy_webp()`.
- **Racional**: Garante conformidade com LGPD/GDPR e mantém o payload de upload ínfimo (< 30 KB), sem expor fotos pessoais dos usuários.

### 3. Journaling Transacional com Separação Salvo vs Pendente
- **Decisão**: Dividir a persistência local do histórico em dois arquivos binários:
  1. `journal_pendente.bin`: Gravação append-only com `pickle.dump(cmd_dict, f)` a cada comando despachado na `QUndoStack`.
  2. `journal_salvo.bin`: Comandos consolidados. No momento do salvamento do croqui (build/commit local), o conteúdo de `journal_pendente.bin` é concatenado ao final de `journal_salvo.bin` e `journal_pendente.bin` é truncado para 0 bytes.
- **Racional**: Permite que, em caso de crash, o editor saiba exatamente quais comandos foram executados após o último salvamento. Se o usuário escolher descartar alterações não salvas, basta limpar o arquivo pendente.

### 4. Formato de Serialização com `pickle` em Modo Append (`"ab"`)
- **Decisão**: Utilizar dicionários puros serializados via `pickle` em modo streaming binário. Cada comando de `editor/commands/` implementa `serializar(redacted=False)` retornando um dicionário com identificador de classe, parâmetros primitivos, caminhos no protobuf e bytes (ou dummy se `redacted=True`).
- **Alternativas consideradas**:
  - *JSON/JSONL textual*: Exigiria codificação Base64 para arrays de bytes de imagens e parsing textual mais lento.
  - *SQLite local*: Overhead desnecessário para uma fila sequencial append-only.
- **Racional**: `pickle` oferece velocidade de microssegundos em C nativo, serialização direta de tipos `bytes` e formato binário compacto.

### 5. Rastreamento de Commit Base (`commit_base_sha`)
- **Decisão**: Incluir `string commit_base_sha = 9` em `CroquiExperimental`. Ao clonar ou instanciar um croqui experimental a partir de um oficial, o SHA atual do branch base em `aresta_db` é gravado no metadado.
- **Racional**: Permite reproduzir 100% dos bugs em ambiente de desenvolvimento rodando os comandos do journal sobre o commit base exato em que o usuário estava trabalhando.

### 6. Migração de `print` para `logging`
- **Decisão**: Implementar `editor/core/logger.py` com configuração de logger centralizado que direciona mensagens para a saída padrão (em desenvolvimento), para `%APPDATA%/editor_aresta/logs/editor.log` (com rotação) e para os breadcrumbs do Sentry.
- **Racional**: Elimina saídas perdidas em `--windowed` e enriquece os relatórios de crash com os eventos cronológicos precedentes.

## Risks / Trade-offs

- **[Risco] Corrupção de arquivo de journal em desligamento abrupto de energia** → *Mitigação*: Leitura com bloco `try/except EOFError` iterativo no `pickle.load`. Se o último comando foi gravado pela metade, os comandos válidos anteriores são lidos normalmente e o último bloco parcial é descartado com segurança.
- **[Risco] Cota de eventos/profiler no plano gratuito do Sentry** → *Mitigação*: A telemetria de crashes envia eventos apenas sob exceções. O profiler pode ser controlado por variável de ambiente ou amostragem segura.
- **[Risco] Vazamento de dados em caminhos customizados fora do padrão Windows** → *Mitigação*: Regex genérico baseado no diretório base do usuário (`Path.home()`) e substituição universal de substrings correspondentes a nomes de login do sistema.
