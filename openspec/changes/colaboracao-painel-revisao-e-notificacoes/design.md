## Context

Com o backend Git Proxy (Sub-projeto 1), a autenticação de autores (Sub-projeto 2) e a engine de commit e push (Sub-projeto 3) totalmente operacionais, o Aresta Editor agora possui suporte nativo para criação e envio de sugestões de croquis. O presente design detalha a arquitetura do **Sub-projeto 4**, focado em trazer transparência, comunicação e agilidade para o fluxo de revisão tanto para o autor da sugestão quanto para o mantenedor responsável.

## Goals / Non-Goals

**Goals:**
- **Biblioteca `ServicoRevisao` (Library-First):** Fornecer uma interface pura, testável e desacoplada para consultar PRs abertas, buscar histórico de comentários/revisões, postar novos comentários e baixar artefatos de branches de sugestão.
- **Aba "Revisão" na `JanelaPrincipal`:** Exibir timeline de discussão do croqui aberto, status do PR no GitHub e caixa de envio de mensagens com atualização do badge de mensagens não lidas.
- **Fila de Aprovação e Gestão de Status na `TelaDeCarregamento`:**
  - Badges visuais de status nos cards (`⚪ Não Enviado`, `🟡 Em Revisão`, `🟢 Aprovado`).
  - Barra de filtros rápidos por status.
  - Seção/Aba dedicada "📥 Para Revisar" para mantenedores com listagem de PRs pendentes da sua alçada.
  - Botão "🔄 Sincronizar" no cabeçalho e sincronização assíncrona na inicialização.
- **Notificações Acionadas pelo GitHub (Backend & CI/CD):**
  - Workflow no GitHub que identifica alterações em `database/<croqui>/`, resolve os mantenedores responsáveis (Code Owners) e aciona a Edge Function do Supabase para disparo de E-mail (Resend) e WhatsApp.

**Non-Goals:**
- Renderização gráfica de Visual Diff lado-a-lado com sobreposição de curvas/canvas (escopo reservado para o Sub-projeto 5).
- Botões de Merge e Rejeição com resolução visual de conflitos (escopo do Sub-projeto 5).

## Decisions & Conformidade com PRINCIPIOS.md

### 1. Princípio I: Tudo em Português Brasileiro
- **Decisão:** Toda a nomenclatura do código (classes, métodos, variáveis, tipos, comentários, logs e documentação) será estritamente em português brasileiro.
  - Ex: `InfoPullRequest`, `ComentarioRevisao`, `StatusCroquiLocal`, `ServicoRevisao`, `listar_sugestoes_pendentes()`, `obter_comentarios_pr()`, `enviar_comentario_pr()`, `baixar_arquivos_sugestao()`, `ultimo_comentario_lido_id`.
  - No backend Deno: `ClienteNotificacao`, `ClienteResend`, `ClienteWhatsapp`, `DadosNotificacaoRevisao`.

### 2. Princípio II: Library-First (Biblioteca em Primeiro Lugar)
- **Decisão:** Toda regra de negócio, protocolo de rede e parsing de dados residirá em bibliotecas puras e autossuficientes, desacopladas de componentes gráficos do PyQt6:
  - `editor/core/servico_revisao.py` não importa PyQt6; aceita parâmetros puros (`requests.Session`, strings, dicionários) e retorna dataclasses tipadas.
  - As views (`PaginaRevisao`, `TelaDeCarregamento`) limitam-se a renderizar as estruturas de dados retornadas pelo serviço e emitir sinais.
  - No backend, módulos desacoplados em `supabase/functions/compartilhado/` (`cliente_resend.ts`, `cliente_whatsapp.ts`, `cliente_notificacao.ts`).

### 3. Princípios III e IV: 100% de Cobertura e TDD Estrito
- **Decisão:** Todo arquivo de código de produção possuirá seu correspondente `_test.py` ou `_test.ts` no mesmo diretório.
  - O desenvolvimento seguirá o ciclo Red $\rightarrow$ Green $\rightarrow$ Refactor:
    1. Escrita do teste unitário falhando (Red).
    2. Implementação do código mínimo para aprovação (Green).
    3. Refatoração e limpeza (Refactor).
  - Cobertura de 100% obrigatória, incluindo todos os ramos condicionais (sucesso, falha de rede 500, autenticação 401/403, dados mal formatados, ausência de PR).

### 4. Princípio V: Testes de Integração em Primeiro Lugar
- **Decisão:** Estabelecer testes de integração de fronteira antes da implementação detalhada dos componentes visuais e regras profundas:
  - `editor/core/integracao_revisao_test.py`: Testa o fluxo completo de consulta de PRs, leitura de timeline, postagem de mensagem e download de artefatos de sugestão contra endpoints simulados.
  - `supabase/functions/integracao_notificacao_revisao_test.ts`: Testa o fluxo do webhook/Edge Function recebendo evento de PR e disparando e-mail e WhatsApp para os mantenedores.

### 5. Princípio VI: Simplicidade e Anti-Abstração
- **Decisão:** Arquitetura direta sem frameworks complexos de gerenciamento de estado global.
  - O estado do badge de comentários não lidos é derivado da comparação simples entre `len(comentarios)` e `ultimo_comentario_lido_id`.
  - A persistência é realizada diretamente em `croqui_experimental.yaml` ou `QSettings`.
  - Sincronização em background utiliza `QThread` / `Worker` padrão já existente no editor.

### 6. Princípio VII: Edições de Estado via Comandos do Histórico (Undo/Redo)
- **Decisão:** A abertura de uma sugestão baixada da comunidade em modo de revisão abre o croqui em um workspace temporário isolado (`tempfile` / staging), garantindo que nenhuma alteração local acidental suje o repositório principal sem passar por comandos rastreados pelo histórico.

## Risks / Trade-offs

- **[Rate Limit da API do GitHub]** → Utilização do token OAuth da sessão do usuário autenticado no cabeçalho `Authorization: Bearer <token>`, elevando o limite para 5.000 requisições/hora, associado a cache leve em memória para metadados de PRs.
- **[Conectividade Offline]** → O editor deve funcionar normalmente sem conexão à internet; se a sincronização falhar, os badges exibem o último estado conhecido ou o status local (`⚪ Não Enviado`) sem travar a interface.
- **[Disponibilidade do Gateway de WhatsApp]** → Falhas no envio de WhatsApp não bloqueiam a criação de PRs ou o envio de e-mails pelo Resend (degradação graciosa com log no backend).
