## Why

O fluxo legado de autenticação do Aresta Editor exigia conta no GitHub e autorização via Device Flow para qualquer usuário, criando uma barreira de entrada alta para escaladores e conquistadores da comunidade que desejam catalogar croquis. Além disso, a ausência de identificação formal do autor impedia a assinatura correta de autoria (`Signed-off-by`) nas contribuições.

Com o novo backend Git Proxy em produção no Supabase, é fundamental implementar no Editor Desktop (PyQt6) uma experiência de login inclusiva e de baixa fricção via **E-mail (Código de 6 dígitos via Supabase Auth / Resend)**, mantendo a autenticação com **GitHub** integrada ao Supabase Auth para mantenedores.

## What Changes

* **Login Primário por E-mail (Código OTP):** Permite login digitando apenas o e-mail e validando o código de 6 dígitos enviado por `nao-responda@login.arestaclimb.com`.
* **Login Secundário com GitHub (Supabase OAuth):** Integração OAuth do Supabase Auth conectada ao GitHub App oficial (`Iv23li5kcnSYgMgEfvAC`), emitindo o JWT do Supabase e entregando o token do GitHub para mantenedores.
* **Captura de Perfil com Pré-preenchimento Inteligente:** Modal de perfil do autor para captura e confirmação do Nome Completo, com **pré-preenchimento automático** a partir do nome público do GitHub (`user_metadata.full_name` ou `name`) quando o usuário se autentica via GitHub OAuth.
* **Sessão Unificada Persistente:** Armazenamento seguro de sessão (`supabase_jwt`, `refresh_token`, `email`, `nome_completo` e `github_token`) no `keyring` do sistema operacional.
* **Interface Gráfica Unificada:** Redesenho completo da tela de autenticação do Editor Desktop com hierarquia visual clara, responsiva e 100% em português brasileiro.

## Capabilities

### New Capabilities
- `editor-perfil-autor`: Captura, pré-preenchimento inteligente a partir do GitHub, validação e persistência do nome completo do autor nos metadados do usuário no Supabase Auth para assinatura de contribuições.

### Modified Capabilities
- `editor-autenticacao`: Atualiza a autenticação do editor para priorizar o fluxo de E-mail OTP via Supabase Auth, integrando o login via GitHub como opção secundária e emitindo JWT de sessão unificado.

## Impact

* **Módulos do Editor Afetados:** `editor/core/cliente_auth_supabase.py`, `editor/core/gerenciador_sessao.py`, `editor/core/servidor_oauth_callback.py`, `editor/core/worker.py`, `editor/views/tela_de_abertura.py`, `editor/views/dialogos/dialogo_autenticacao.py` e `editor/views/dialogos/dialogo_perfil_autor.py`.
* **Dependências Externas:** `requests` para chamadas HTTP REST, `keyring` para persistência segura de credenciais do sistema operacional e `http.server` para callback OAuth.
* **Aderência aos Princípios:** Estrutura 100% em português brasileiro, desenvolvimento orientado a testes (TDD com 100% de cobertura), arquitetura Library-First e testes de integração de fronteira.
