## 1. Testes de Integração de Fronteira e Biblioteca Core de Revisão (Princípios II, III, IV e V)

- [ ] 1.1 Criar teste de integração de fronteira cobrindo o fluxo completo de consulta de PRs, leitura de timeline de comentários e download de arquivos em `editor/core/integracao_revisao_test.py`
- [ ] 1.2 Implementar dataclasses `InfoPullRequest`, `ComentarioRevisao`, `StatusCroquiLocal` e funções de consulta de status de PRs em `editor/core/servico_revisao.py` via TDD estrito com 100% de cobertura em `editor/core/servico_revisao_test.py`
- [ ] 1.3 Implementar funções de listagem de comentários e envio de novos comentários de PR em `editor/core/servico_revisao.py` via TDD estrito com 100% de cobertura em `editor/core/servico_revisao_test.py`
- [ ] 1.4 Implementar função de download de arquivos de sugestão para diretório de staging temporário em `editor/core/servico_revisao.py` via TDD estrito com 100% de cobertura em `editor/core/servico_revisao_test.py`
- [ ] 1.5 Implementar lógica de persistência e cálculo de comentários não lidos (`ultimo_comentario_lido_id`) em `editor/core/servico_revisao.py` via TDD estrito com 100% de cobertura em `editor/core/servico_revisao_test.py`

## 2. Aba Lateral "Revisão" na Janela Principal (Princípios I, III, IV e VII)

- [ ] 2.1 Implementar componente visual `PaginaRevisao` em `editor/views/pagina_revisao.py` exibindo metadados da PR, timeline de discussão e formulário de resposta via TDD com 100% de cobertura em `editor/views/pagina_revisao_test.py`
- [ ] 2.2 Integrar a 4ª aba lateral oficial "Revisão" na `JanelaPrincipal` em `editor/legacy_views/area_principal.py` com navegação e carregamento assíncrono via TDD com 100% de cobertura em `editor/legacy_views/area_principal_test.py`
- [ ] 2.3 Implementar badge numérico visual de comentários não lidos na barra lateral de navegação da `JanelaPrincipal` via TDD com 100% de cobertura em `editor/legacy_views/area_principal_test.py`

## 3. Gestão de Fila de Aprovação e Filtros na Tela de Carregamento (Princípios I, III, IV e VI)

- [ ] 3.1 Implementar componente de badges de status (`Não Enviado`, `Em Revisão`, `Aprovado`) e comentários não lidos nos cards de croquis em `editor/legacy_views/tela_de_carregamento.py` via TDD em `editor/legacy_views/tela_de_carregamento_test.py`
- [ ] 3.2 Implementar barra de filtros rápidos por status na `TelaDeCarregamento` via TDD com 100% de cobertura em `editor/legacy_views/tela_de_carregamento_test.py`
- [ ] 3.3 Implementar aba "Para Revisar" listando PRs abertas de croquis sob responsabilidade do usuário com botões de ação via TDD em `editor/legacy_views/tela_de_carregamento_test.py`
- [ ] 3.4 Implementar botão "Sincronizar" no cabeçalho e sincronização em background na `TarefaInicializacao` (`editor/core/worker.py`) via TDD com 100% de cobertura em `editor/core/worker_test.py`

## 4. Backend e Automação de Notificações (Princípios I, II, III, IV e V)

- [ ] 4.1 Criar migração SQL `20260826000000_criar_tabela_mantenedores_croquis.sql` no Supabase com políticas RLS em `../aresta_backend/supabase/migrations/`
- [ ] 4.2 Criar teste de integração de fronteira para notificação de mantenedores em `../aresta_backend/supabase/functions/integracao_notificacao_revisao_test.ts`
- [ ] 4.3 Implementar módulos desacoplados `cliente_resend.ts` e `cliente_whatsapp.ts` em `../aresta_backend/supabase/functions/compartilhado/` via TDD com 100% de cobertura em `cliente_resend_test.ts` e `cliente_whatsapp_test.ts`
- [ ] 4.4 Implementar Edge Function `notificar-revisao` no Supabase (`../aresta_backend/supabase/functions/notificar-revisao/`) via TDD com 100% de cobertura em `index_test.ts`
- [ ] 4.5 Criar workflow do GitHub Actions `.github/workflows/notificar-mantenedores.yml` no repositório `aresta_db` disparado em eventos de PRs de sugestão
