## Context

O **Aresta Editor** (PyQt6) atualmente possui autenticação exclusiva via GitHub Device Flow (`editor/core/auth.py`). O Sub-projeto 1 concluiu a implantação do backend no Supabase (`git-proxy` e `create-pr`), o qual requer tokens JWT emitidos pelo Supabase Auth contendo a identificação do autor (`email` e `nome_completo`).

Este documento especifica a arquitetura técnica do **Sub-projeto 2: Autenticação por E-mail (OTP) do Supabase e Perfil do Autor**, em estrita conformidade com as diretrizes do [`PRINCIPIOS.md`](file:///c:/Renato/Devel/aresta-climb/aresta_db/PRINCIPIOS.md).

## Goals / Non-Goals

**Goals:**
* Implementar a biblioteca modular `ClienteAuthSupabase` em `editor/core/cliente_auth_supabase.py` consumindo os endpoints REST do Supabase Auth (`/otp`, `/verify`, `/user`, `/token`).
* Implementar a biblioteca de sessão `GerenciadorSessao` em `editor/core/gerenciador_sessao.py` com persistência segura em `keyring` e auto-renovação de JWT.
* Implementar o servidor efêmero de callback `ServidorCallbackOAuth` em `editor/core/servidor_oauth_callback.py` para login OAuth com GitHub.
* Criar componentes visuais PyQt6 desacoplados em português:
  * `editor/views/dialogos/dialogo_autenticacao.py`: Entrada de e-mail, seleção de método e validação do código OTP de 6 dígitos.
  * `editor/views/dialogos/dialogo_perfil_autor.py`: Diálogo modal para captura e confirmação do Nome Completo, com **pré-preenchimento automático** do nome vindo do GitHub.
* Integrar o fluxo na `TelaDeAbertura` e na `TarefaInicializacao` (`editor/core/worker.py`).
* Garantir 100% de cobertura de testes unitários e de integração de fronteira com TDD rigoroso.

**Non-Goals:**
* Não abrange operações de commit e push com `pygit2` (escopo do Sub-projeto 3).
* Não abrange moderação e listagem de Pull Requests (escopo dos Sub-projetos 4 e 5).

## Decisions

### Decisão 1: Princípio I (Tudo em Português Brasileiro)
* Todos os novos módulos, classes, métodos, variáveis e testes são nomeados exclusivamente em português brasileiro:
  * `ClienteAuthSupabase`: `solicitar_codigo_otp()`, `verificar_codigo_otp()`, `atualizar_nome_autor()`, `renovar_sessao()`, `obter_usuario_atual()`.
  * `GerenciadorSessao`: `salvar_sessao()`, `obter_sessao()`, `limpar_sessao()`, `sessao_valida()`.
  * `SessaoUsuario`: `email`, `nome_completo`, `jwt_supabase`, `token_atualizacao`, `token_github`.
  * `ServidorCallbackOAuth`: `iniciar_escuta()`, `aguardar_tokens()`, `encerrar()`.
  * `DialogoAutenticacao` e `DialogoPerfilAutor`.

### Decisão 2: Princípio II (Library-First) e VI (Simplicidade)
* **Biblioteca Autônoma:** `ClienteAuthSupabase` é uma biblioteca pura em `editor/core/`, desacoplada de PyQt6, operando de forma síncrona com `requests`.
* **Sem dependências externas desnecessárias:** Evita a complexidade do SDK assíncrono do Supabase, utilizando chamadas REST declarativas diretas.

### Decisão 3: Princípio IV (TDD) e V (Testes de Integração em Primeiro Lugar)
* **Testes de Integração:** Criação de `editor/core/integracao_auth_supabase_test.py` testando o ciclo completo de autenticação contra contratos de mock de endpoints do Supabase Auth e servidor local de callback.
* **Testes Unitários (100% de Cobertura):** Cada arquivo `.py` possui seu respectivo `_test.py` no mesmo diretório (`cliente_auth_supabase_test.py`, `gerenciador_sessao_test.py`, `servidor_oauth_callback_test.py`, `dialogo_autenticacao_test.py`, `dialogo_perfil_autor_test.py`).

### Decisão 4: Modelo de Sessão Unificada e Keyring
* A classe `SessaoUsuario` encapsula a identidade do usuário. O `GerenciadorSessao` utiliza o `keyring` do sistema sob o serviço `aresta_editor`. Em ambientes de teste ou sem keyring disponível, utiliza um backend em memória de fallback.

### Decisão 5: Pré-preenchimento Inteligente e Validação de Nome Completo
* Ao autenticar via GitHub OAuth, o Supabase Auth injeta nos metadados do usuário (`user_metadata`) os campos `full_name` ou `name` públicos da conta do GitHub.
* O `DialogoPerfilAutor` inspeciona a hierarquia: `nome_completo` -> `full_name` -> `name`. Se encontrar um valor, pré-preenche o campo de texto automaticamente.
* O usuário pode apenas confirmar o nome ou editá-lo caso deseje. A validação exige ao menos 2 palavras (nome e sobrenome), e a confirmação persiste via `PUT /auth/v1/user` (`{"data": {"nome_completo": "..."}}`).

## Risks / Trade-offs

* **[Porta de callback OAuth em uso]** → `ServidorCallbackOAuth` vincula ao socket com porta `0` (`localhost:0`), deixando o sistema operacional alocar uma porta livre automaticamente e repassando-a para a URL de `redirect_to`.
* **[Token JWT expirado durante a sessão]** → `GerenciadorSessao` verifica se o token está próximo do vencimento e utiliza `ClienteAuthSupabase.renovar_sessao()` para renovar silenciosamente via `refresh_token`.
* **[Ambientes de CI/Testes sem keyring nativo]** → Suporte a `KeyringMemoria` para que 100% dos testes executem sem dependências do sistema operacional.
