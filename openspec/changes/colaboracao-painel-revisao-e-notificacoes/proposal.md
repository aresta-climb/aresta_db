## Why

Com a engine de submissão (Sub-projeto 3) operacional, contribuidores da comunidade agora enviam sugestões de croquis via Pull Requests automatizadas. No entanto, o fluxo de colaboração carece de visibilidade e comunicação no cliente Desktop: os mantenedores não possuem uma interface integrada para visualizar as sugestões pendentes sob sua responsabilidade, os autores não conseguem acompanhar a conversa e os feedbacks da PR diretamente no editor, e não há um sistema de alerta ativo (E-mail e WhatsApp) disparado pelo GitHub para avisar os mantenedores quando uma nova revisão é solicitada.

Implementar a aba de Revisão, a fila de aprovação com filtros e badges na tela inicial, a sincronização em background e as notificações acionadas pelo GitHub fecha o ciclo de colaboração assíncrona com mínima fricção, seguindo rigorosamente os princípios de engenharia de software do projeto.

## What Changes

- **Aba Lateral "Revisão" na `JanelaPrincipal`:**
  - Adição da 4ª aba lateral oficial ("Revisão") dedicada ao croqui aberto.
  - Exibição de metadados da Pull Request vinculada (status, branch, autor, data, link externo).
  - Linha do tempo interativa com histórico cronológico de comentários e revisões do GitHub.
  - Caixa de texto e botão para envio de comentários e respostas do autor ou mantenedor diretamente pelo Editor.
  - Badge numérico no ícone da barra lateral indicando comentários não lidos (`💬 (N)`).
- **Fila de Aprovação e Gestão de Status na `TelaDeCarregamento`:**
  - Badges visuais de status em cada card de croqui local: `⚪ Não Enviado` (local/sem PR), `🟡 Em Revisão` (PR aberta), `🟢 Aprovado` (PR merged) e indicador de novos comentários `💬 (N)`.
  - Barra de filtros rápidos por status no topo da lista (`Todos`, `Não Enviado`, `Em Revisão`, `Aprovado`).
  - Nova aba/seção dedicada **"📥 Para Revisar"** exclusiva para mantenedores, listando as Pull Requests abertas que demandam a sua aprovação (filtradas pelos croquis sob sua responsabilidade).
  - Botão **"🔄 Sincronizar"** no cabeçalho para atualização manual sob demanda.
  - Sincronização assíncrona automática em segundo plano durante a inicialização do app (`TarefaInicializacao`) sem bloquear a renderização da interface.
- **Mecanismo de Download Temporário de Sugestões:**
  - Capacidade de baixar os arquivos da branch de uma sugestão para uma pasta temporária de staging, permitindo abrir o croqui no editor em modo de inspeção/revisão.
- **Notificações Acionadas pelo GitHub (Backend & CI/CD):**
  - Cadastro de mantenedores e preferências de contato (E-mail e WhatsApp) no backend Supabase (`aresta_backend`).
  - Workflow no GitHub Actions / Webhook acionado na abertura ou atualização de Pull Requests que identifica o croqui modificado, consulta os Code Owners / Mantenedores responsáveis e dispara notificações via Resend (E-mail) e WhatsApp Gateway.
- **Aderência Estrita a `PRINCIPIOS.md`:**
  - **Princípio I (Tudo em Português):** Código, módulos, classes, métodos, variáveis, testes, documentação e mensagens 100% em português brasileiro.
  - **Princípio II (Library-First):** Extração de bibliotecas puras e autossuficientes (`editor/core/servico_revisao.py`, `cliente_notificacao.ts`, `cliente_resend.ts`, `cliente_whatsapp.ts`).
  - **Princípios III e IV (100% Cobertura & TDD):** Ciclo Red $\rightarrow$ Green $\rightarrow$ Refactor com arquivos `_test.py` / `_test.ts` acompanhando cada módulo com cobertura total de branches.
  - **Princípio V (Testes de Integração em Primeiro Lugar):** Criação inicial de testes de integração de fronteira (`editor/core/integracao_revisao_test.py` e `supabase/functions/integracao_notificacao_revisao_test.ts`).
  - **Princípio VI (Simplicidade e Anti-Abstração):** Código declarativo, simples, sem abstrações convolutas.
  - **Princípio VII (Histórico Undo/Redo):** Isolamento de staging e proteção de histórico de edição.

## Capabilities

### New Capabilities
- `editor-painel-revisao`: Interface e serviço da 4ª aba lateral do Editor para visualização de linha do tempo de comentários de PRs, envio de mensagens e contagem de mensagens não lidas.
- `editor-fila-aprovacao`: Gestão de status de croquis locais, filtros por status, aba de fila de pendências para mantenedores e sincronização assíncrona na tela inicial.
- `backend-notificacoes-revisao`: Mecanismo de notificação proativa acionado por eventos do GitHub que identifica os mantenedores responsáveis pelo croqui e envia alertas via E-mail (Resend) e WhatsApp.

### Modified Capabilities
- `editor-tela-de-carregamento`: Atualizada para incorporar badges de status nos cards, barra de filtros rápidos, contadores e botão de re-sincronização.

## Impact

- **Código Afetado no Desktop (`aresta_db`):**
  - `editor/core/integracao_revisao_test.py` (teste de integração de fronteira fim-a-fim).
  - `editor/core/servico_revisao.py` e `editor/core/servico_revisao_test.py` (nova biblioteca library-first com 100% de cobertura).
  - `editor/views/pagina_revisao.py` e `editor/views/pagina_revisao_test.py` (nova view da 4ª aba).
  - `editor/legacy_views/area_principal.py` e `editor/legacy_views/area_principal_test.py` (integração da aba "Revisão" e badges).
  - `editor/legacy_views/tela_de_carregamento.py` e `editor/legacy_views/tela_de_carregamento_test.py` (filtros, badges, aba "Para Revisar", botão sincronizar).
  - `editor/core/worker.py` e `editor/core/worker_test.py` (sincronização assíncrona em background).
- **Código Afetado no Backend & CI/CD (`aresta_backend` & `aresta_db`):**
  - Migração SQL `20260826000000_criar_tabela_mantenedores_croquis.sql` no Supabase com RLS.
  - `supabase/functions/notificar-revisao/index.ts` e `index_test.ts`.
  - `supabase/functions/compartilhado/cliente_notificacao.ts` e `cliente_notificacao_test.ts`.
  - `supabase/functions/compartilhado/cliente_resend.ts` e `cliente_resend_test.ts`.
  - `supabase/functions/compartilhado/cliente_whatsapp.ts` e `cliente_whatsapp_test.ts`.
  - `supabase/functions/integracao_notificacao_revisao_test.ts`.
  - Workflow `.github/workflows/notificar-mantenedores.yml` no repositório `aresta_db`.
