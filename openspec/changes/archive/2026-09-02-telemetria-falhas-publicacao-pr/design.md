## Context

O Aresta Editor Desktop publica sugestões de edição de croquis através de um fluxo coordenado pela biblioteca `ServicoSubmissao` em conjunto com a thread de interface `TarefaPublicacao` (`editor/core/worker.py`).

Atualmente, qualquer falha durante este fluxo (seja falha de autenticação Supabase, travamento pygit2, rejeição no firewall do `git-proxy` ou erro na Edge Function `create-pr`) é capturada no bloco `except Exception:` da thread `TarefaPublicacao`, emitindo o sinal `self.erro.emit(str(e))` para a interface gráfica. Como a exceção é tratada dentro da thread, ela nunca atinge os ganchos globais de exceção (`sys.excepthook` e `threading.excepthook`), tornando as falhas de submissão 100% invisíveis para a telemetria do Sentry.

Este documento projeta a integração de telemetria ativa, categorizada e enriquecida, estritamente estruturada conforme os princípios de engenharia de software descritos em `PRINCIPIOS.md`:
1. **Tudo em Português**: Nomenclaturas, funções, variáveis, docstrings, comentários e tags de telemetria integralmente em português brasileiro.
2. **Library-First**: Bibliotecas puras, isoladas e modulares em `editor/core/telemetria.py` e `editor/core/servico_submissao.py`.
3. **100% de Cobertura de Testes Unitários**: Cobertura integral de todos os ramos de código novo e modificado.
4. **Imperativo do TDD (Red-Green-Refactor)**: Todo arquivo `.py` acompanhado pelo respectivo `_test.py` no mesmo diretório.
5. **Testes de Integração em Primeiro Lugar**: Testes de contrato de fronteira entre `ServicoSubmissao` e o despachante de telemetria estabelecidos antes dos testes de unidade profundos.
6. **Simplicidade e Anti-Abstração**: Funções diretas, declarativas e sem camadas desnecessárias de abstração.
7. **Edições de Estado via Comandos do Histórico**: Preservação do diário de comandos recente no anexo de telemetria para diagnóstico determinístico.

## Goals / Non-Goals

**Goals:**
- Prover telemetria em tempo real com severidade crítica (`fatal` / `error`) para todas as falhas de upload de propostas de mudança.
- Implementar categorização estruturada (`categoria_erro`: `git_proxy`, `github_api`, `git_local`, `autenticacao`, `rede`, `inesperado`) para permitir filtros e alertas precisos no Sentry.
- Gravar breadcrumbs cronológicos das etapas de publicação (`reportar(pct, msg)`), permitindo inspecionar a sequência exata de passos antes da falha.
- Anexar o diário de comandos recente anonimizado e contexto operacional sanitizado (código de status HTTP, corpo de resposta de erro, branch, ID do croqui).
- Garantir 100% de cobertura de testes unitários com TDD em `editor/core/telemetria_test.py`, `editor/core/servico_submissao_test.py` e `editor/core/worker_test.py`.

**Non-Goals:**
- Não altera o protocolo de comunicação Git Smart HTTP via `git-proxy` nem os contratos de API das Edge Functions.
- Não altera o visual das caixas de diálogo (`QMessageBox`) de erro para o usuário final.
- Não introduz dependências externas novas (utiliza `sentry_sdk` já configurado no projeto).

## Decisions

### 1. Centralização da Telemetria de Submissão em `editor/core/telemetria.py` (*Library-First* & *Anti-Abstração*)
- **Decisão**: Criar a função utilitária direta `capturar_falha_submissao(erro: Exception, id_croqui: str, etapa: str, categoria: str, contexto_extra: Optional[Dict[str, Any]] = None) -> Optional[str]` e `registrar_breadcrumb_submissao(mensagem: str, categoria: str = "submissao_pr", dados: Optional[Dict[str, Any]] = None) -> None`.
- **Racional**: Mantém a lógica de formatação de escopo Sentry, anexos de diário e sanitização de dados dentro do módulo de telemetria, evitando poluir o `ServicoSubmissao` com acoplamento direto ao SDK do Sentry.
- **Alternativa Considerada**: Criar uma classe abstrata `ProvedorTelemetria` com subclasses e injeção de dependência via factory. Descartado em conformidade com o princípio de *Simplicidade e Anti-Abstração* ("Melhor um pouco de duplicação do que a abstração errada").

### 2. Taxonomia de Categorias e Níveis de Severidade (100% em Português)
- **Decisão**: Mapear as falhas nas seguintes categorias e níveis:
  - `git_proxy`: Nível `fatal` (falhas no proxy ou streaming HTTP de packfile).
  - `github_api`: Nível `fatal` (código de status != 200 na Edge Function `create-pr` ou na API do GitHub).
  - `git_local`: Nível `fatal` (erros de I/O, checkout, pygit2 index/commit).
  - `autenticacao`: Nível `error` (sessão revogada ou falha irrecuperável de renovação de token).
  - `rede`: Nível `warning` (falhas de conexão, DNS ou timeout).
  - `inesperado`: Nível `fatal` (qualquer exceção residual).
- **Racional**: Permite que a equipe de engenharia crie alertas prioritários imediatos (Discord/Slack/Email) para falhas de infraestrutura e bugs (`fatal`), enquanto acompanha falhas de sessão e rede em dashboards de monitoramento.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Taxonomia de Erros de Submissão no Sentry                              │
├────────────────────────────────────────────────────────────────────────┤
│ • git_proxy    ─▶ Nível FATAL  ─▶ Alerta Imediato                      │
│ • github_api   ─▶ Nível FATAL  ─▶ Alerta Imediato                      │
│ • git_local    ─▶ Nível FATAL  ─▶ Alerta Imediato                      │
│ • autenticacao ─▶ Nível ERROR  ─▶ Monitoramento de Sessões             │
│ • rede         ─▶ Nível WARN   ─▶ Métricas de Conectividade            │
│ • inesperado   ─▶ Nível FATAL  ─▶ Alerta Imediato                      │
└────────────────────────────────────────────────────────────────────────┘
```

### 3. Emissão de Breadcrumbs Automáticos por Etapa
- **Decisão**: No método `submeter_sugestao` do `ServicoSubmissao`, cada avanço registrado na função auxiliar `reportar(porcentagem, mensagem)` disparará também um breadcrumb no Sentry (`categoria="submissao_pr"`).
- **Racional**: Permite que ao abrir um evento de erro no painel do Sentry, a lista de breadcrumbs mostre cronologicamente até onde o envio progrediu (ex: `10% Verificando autenticação`, `40% Sincronizando arquivos`, `60% Gerando commit`, `80% Enviando alterações`).

### 4. Logging Estruturado e Fallback na `TarefaPublicacao`
- **Decisão**: Substituir o `traceback.print_exc()` genérico em `TarefaPublicacao.run()` por `logger.critical(..., exc_info=True)` e assegurar que exceções não tratadas fora do `ServicoSubmissao` também sejam registradas na telemetria.
- **Racional**: Garante que erros de inicialização de parâmetros ou falhas na thread nunca fiquem invisíveis.

### 5. Sanitização de Privacidade e Proteção de Dados
- **Decisão**: Toda mensagem de erro, URL e contexto de exceção passa por `sanitizar_texto_caminhos` e pelo gancho `sanitizar_evento_sentry`. Nenhum token de autenticação (JWT) nem caminho de diretório local é enviado em texto plano.

## Risks / Trade-offs

- **[Risco] Falha na inicialização do Sentry ou falta de conexão à internet no envio do erro**
  → *Mitigação*: `capturar_falha_submissao` possui bloco `try...except` interno protetor que silencia qualquer erro de telemetria, garantindo que o `ErroSubmissao` original seja entregue intacto para a UI.
- **[Risco] Falta de cobertura de testes em cenários de exceção de rede ou pygit2**
  → *Mitigação*: Criação de testes unitários e de integração mockando falhas em cada etapa, validando que 100% das linhas e branches de tratamento de erro são exercitadas no `pytest`.
