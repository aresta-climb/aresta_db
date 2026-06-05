## 1. Infraestrutura e Dependências

- [x] 1.1 Adicionar `pygithub`, `pygit2` e `keyring` ao `editor/requirements.txt`.
- [x] 1.2 Refatorar `editor/core/storage.py` para usar `aresta_db` como nome da pasta local.
- [x] 1.3 Renomear todas as classes e variáveis para Português conforme `PRINCIPIOS.md`.

## 2. Autenticação (Library-First & TDD)

- [x] 2.1 Criar `editor/core/auth.py` com suporte a Device Flow.
- [x] 2.2 Integrar `keyring` para persistência segura de tokens.
- [x] 2.3 Implementar validação de token e tratamento de erros de rede.

## 3. Sincronização Git com pygit2

- [x] 3.1 Implementar `GerenciadorSincronizacao` com suporte a `pygit2`.
- [x] 3.2 **Extra**: Implementar `RemoteCallbacks.credentials` para suportar repositórios privados (401).
- [x] 3.3 Implementar lógica de fork automático e clone de upstream.
- [x] 3.4 Reportar progresso real de download para a UI.

## 4. Interface da Tela de Abertura (UI/UX)

- [x] 4.1 Criar `TelaDeAbertura` com layout frameless e estética premium.
- [x] 4.2 **Extra**: Estilizar barra de progresso (Cores, Fontes e Visibilidade dinâmica).
- [x] 4.3 **Extra**: Refinar layout de autenticação (Instruções em múltiplas linhas, centralização de widgets).
- [x] 4.4 Implementar `TarefaInicializacao` em background via sinais.

## 5. Integração e Polimento

- [x] 5.1 Orquestrar ciclo de vida no `main.py` (Tela de Abertura -> Janela Principal).
- [x] 5.2 **Extra**: Corrigir ordem de janelas em caso de erro (esconder Splash antes do QMessageBox).
- [x] 5.3 Implementar suíte de testes (17 testes automatizados passando).
- [x] 5.4 Adicionar logs detalhados no terminal para facilitar depuração.
