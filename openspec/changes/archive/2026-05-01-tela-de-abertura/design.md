## Contexto

Atualmente, o Editor Aresta não possui um fluxo de inicialização robusto. Ele depende do `git` instalado no sistema e não autentica o usuário. A implementação da `TelaDeAbertura` resolve esses problemas, garantindo que o ambiente de trabalho esteja pronto e o autor identificado.

## Objetivos / Não-Objetivos

**Objetivos:**
- Implementar uma tela de abertura (`TelaDeAbertura`) que realize tarefas de rede e disco em background.
- Garantir que o código siga rigorosamente o `PRINCIPIOS.md` (Tudo em Português).
- Implementar login via GitHub usando o fluxo de dispositivo (Device Flow).
- Sincronizar o repositório privado `aresta-climb/aresta_db` localmente na pasta `aresta_db`.

**Não-Objetivos:**
- Implementar edição de croquis nesta fase.
- Implementar troca de repositório (o foco é o repositório base da organização).

## Decisões

### 1. Arquitetura em Português e Orientada a Sinais
Todas as classes foram renomeadas para Português:
- `SplashScreen` -> `TelaDeAbertura`
- `WorkerInicializacao` -> `TarefaInicializacao`
- `ControladorApp` -> `ControladorAplicativo`
- `GerenciadorSync` -> `GerenciadorSincronizacao`
A comunicação é feita via sinais (`pyqtSignal`), garantindo desacoplamento entre a lógica de background e a interface.

### 2. Autenticação GitHub com Device Flow
O app solicita permissão via código de 8 dígitos. As instruções foram refinadas para serem explicativas e amigáveis, com suporte a múltiplas linhas e fonte ampliada (**14px**).

### 3. Sincronização de Repositórios Privados
Para lidar com repositórios privados da organização `aresta-climb`:
- **404 (Not Found)**: Detectado quando o App não tem permissão na organização. O sistema emite um erro instruindo o usuário a conceder acesso.
- **401 (Unauthorized)**: Resolvido através da implementação de `pygit2.RemoteCallbacks.credentials`, que injeta o token OAuth2 nas operações de clone e fetch.

### 4. Estética Premium e UX
- **Barra de Progresso**: Estilizada com fundo `#24283b` e destaque azul `#7aa2f7`. Exibida apenas durante operações Git para reduzir ruído visual.
- **Tratamento de Erros**: Se ocorrer um erro fatal, a `TelaDeAbertura` é ocultada antes da exibição do `QMessageBox`, garantindo que a janela de erro não fique presa atrás da Splash Screen.

### 5. Storage
O repositório local é armazenado em `%APPDATA%\editor_aresta\aresta_db` (no Windows), mantendo a nomenclatura original do projeto.

## Riscos / Trade-offs

- **[Risco] Permissões de Organização** → **Mitigação**: Mensagens de erro claras detectando especificamente o 404 em repositórios privados.
- **[Risco] Autenticação Git** → **Mitigação**: Uso de `UserPass` no `pygit2` injetando o token como senha (`x-oauth-basic`).
