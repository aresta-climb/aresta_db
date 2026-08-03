## Why

Para garantir integridade de dados ao longo do tempo. Quando usuários deixam o Editor Aresta aberto por longos períodos (dias seguidos), eles contornam qualquer mecanismo futuro de auto-update acionado na inicialização do aplicativo (boot). Isso cria uma brecha perigosa onde croquis podem ser publicados com esquemas estruturais desatualizados caso um release tenha sido feito durante o tempo de uso da pessoa. Inserir uma trava rígida (hard block) imediatamente antes do fluxo de publicação impede que dados corrompidos ou defasados entrem no banco de dados.

## What Changes

- **Guarda de Trânsito no Publish**: O `PublishController` (`iniciar_publicacao`) fará uma checagem mandatória da versão mais recente do repositório antes mesmo de checar modificações locais ou montar a Pull Request.
- **Requisição Assíncrona via Token**: A chamada ao GitHub API (`GET /releases/latest`) será feita de forma assíncrona exibindo uma barra de progresso, e utilizará o token de autenticação (já presente em `self.auth`) para burlar limites de Rate Limiting.
- **Hard Block & Restart**: Se o aplicativo constatar que está desatualizado, o processo de publicação é abortado instantaneamente. Um alerta forçará o usuário a reiniciar o editor (gatilho que iniciará o download automático assumido para a Fase 3).

## Capabilities

### New Capabilities
- `publish-version-guard`: Trava de segurança inserida no fluxo de publicação, responsável pela interface e regra de checagem.

### Modified Capabilities

## Impact

- Modificações focadas e encapsuladas na view de diálogo de publicação e no `PublishController`.
- Fluxo de UX levemente estendido: todo publish exibirá por milissegundos uma tela de "Verificando versão...".
- Usuários de longa-sessão serão abruptamente interrompidos e não terão opção de ignorar o update.
