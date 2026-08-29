# Tarefas de Implementação: Onda 2 - Tipagem Estática do Núcleo de Dados, Modelos e Core

## 1. Fundação, Utilitários e Armazenamento

- [x] 1.1 Anotar com tipagem estática estrita os módulos `editor/core/version.py`, `editor/core/formatacao.py` e `editor/core/storage.py`.
- [x] 1.2 Anotar com tipagem estática estrita os módulos `editor/core/contexto.py`, `editor/core/coordenadas.py` e `editor/core/geometrias_poi.py`.

## 2. Workspace, Imagens e Formatos de Croqui

- [x] 2.1 Anotar com tipagem estática estrita os módulos `editor/core/croqui_format.py`, `editor/core/croqui_experimental.py` e `editor/core/proto_comments.py`.
- [x] 2.2 Anotar com tipagem estática estrita os módulos `editor/core/workspace.py`, `editor/core/imagens_markdown.py` e `editor/core/processamento_imagem_campo.py`.
- [x] 2.3 Anotar com tipagem estática estrita os módulos `editor/core/imagem_anonimizada.py` e fluxos de export/import.

## 3. Sessão, Rede, Submissão e Workers

- [x] 3.1 Anotar com tipagem estática estrita os módulos `editor/core/gerenciador_sessao.py` e `editor/core/cliente_auth_supabase.py`.
- [x] 3.2 Anotar com tipagem estática estrita os módulos `editor/core/servico_submissao.py`, `editor/core/servico_loja.py` e `editor/core/sync.py`.
- [x] 3.3 Anotar com tipagem estática estrita os módulos `editor/core/worker.py`, `editor/core/atualizador_ui.py` e `editor/core/monitor_inatividade.py`.

## 4. Histórico, Diário, Telemetria e Logs

- [x] 4.1 Anotar com tipagem estática estrita os módulos `editor/core/historico.py`, `editor/core/diario.py`, `editor/core/registro_log.py` e `editor/core/telemetria.py`.

## 5. Integração com Teste Guardião e Validação Global

- [x] 5.1 Atualizar `tests/tipagem_estatica_test.py` para incluir todos os módulos de `editor/core/` na verificação MyPy estrita e metateste AST.
- [x] 5.2 Executar a suíte completa de testes unitários (`pytest`) e validar 100% de aprovação e integridade.

