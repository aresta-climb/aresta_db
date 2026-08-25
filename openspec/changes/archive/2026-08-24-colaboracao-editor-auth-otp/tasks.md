## 1. Testes de Integração de Fronteira (Princípio V)

- [x] 1.1 Criar suite de testes de integração `editor/core/integracao_auth_supabase_test.py` cobrindo o ciclo de login OTP, validação de token, renovação de sessão, callback OAuth e pré-preenchimento de perfil

## 2. Biblioteca de Sessão e Persistência Segura (Library-First)

- [x] 2.1 Criar testes unitários para `SessaoUsuario` e `GerenciadorSessao` em `editor/core/gerenciador_sessao_test.py`
- [x] 2.2 Implementar dataclass `SessaoUsuario` e a classe `GerenciadorSessao` com suporte a keyring e fallback em memória em `editor/core/gerenciador_sessao.py`

## 3. Biblioteca Cliente REST do Supabase Auth (Library-First)

- [x] 3.1 Criar suite de testes unitários com mocks para `ClienteAuthSupabase` em `editor/core/cliente_auth_supabase_test.py`
- [x] 3.2 Implementar método `solicitar_codigo_otp(email)` conectando ao endpoint `/auth/v1/otp` em `editor/core/cliente_auth_supabase.py`
- [x] 3.3 Implementar método `verificar_codigo_otp(email, token)` conectando ao endpoint `/auth/v1/verify` em `editor/core/cliente_auth_supabase.py`
- [x] 3.4 Implementar método `atualizar_nome_autor(jwt, nome_completo)` conectando ao endpoint `/auth/v1/user` em `editor/core/cliente_auth_supabase.py`
- [x] 3.5 Implementar métodos `renovar_sessao(refresh_token)` e `obter_usuario_atual(jwt)` em `editor/core/cliente_auth_supabase.py`

## 4. Biblioteca do Servidor de Callback OAuth para GitHub (Library-First)

- [x] 4.1 Criar testes unitários para `ServidorCallbackOAuth` em `editor/core/servidor_oauth_callback_test.py`
- [x] 4.2 Implementar `ServidorCallbackOAuth` com alocação dinâmica de porta em `editor/core/servidor_oauth_callback.py`

## 5. Interface Gráfica de Autenticação e Perfil (PyQt6 Views)

- [x] 5.1 Criar testes unitários para `DialogoPerfilAutor` em `editor/views/dialogos/dialogo_perfil_autor_test.py` incluindo casos de pré-preenchimento vindo do GitHub
- [x] 5.2 Implementar componente visual `DialogoPerfilAutor` com pré-preenchimento inteligente e validação de nome em `editor/views/dialogos/dialogo_perfil_autor.py`
- [x] 5.3 Criar testes unitários para `DialogoAutenticacao` em `editor/views/dialogos/dialogo_autenticacao_test.py`
- [x] 5.4 Implementar componente visual `DialogoAutenticacao` com fluxo de E-mail OTP primário, contagem regressiva de reenvio e botão secundário de GitHub em `editor/views/dialogos/dialogo_autenticacao.py`

## 6. Integração com o Ciclo de Inicialização do Editor

- [x] 6.1 Atualizar `editor/core/worker.py` (`TarefaInicializacao`) para validar sessão unificada do Supabase Auth e orquestrar novos diálogos
- [x] 6.2 Atualizar `editor/views/tela_de_abertura.py` para integrar o novo fluxo de login unificado
- [x] 6.3 Atualizar testes existentes em `editor/core/worker_test.py` e `editor/views/tela_de_abertura_test.py`

## 7. Validação Completa de Testes e Cobertura

- [x] 7.1 Executar a suite completa de testes do Editor (`pytest`) e assegurar 100% de testes passando sem regressões
