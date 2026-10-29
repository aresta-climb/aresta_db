# retransmissor-nuvem-previa Specification

## Purpose

Define o comportamento do Cloudflare Worker (`previa.arestaclimb.com`) responsável por gerenciar sessões efêmeras de prévia ao vivo do Editor Desktop e rotear de forma stateless prévias semi-permanentes e resumos visuais de Pull Requests.

## Requirements

### Requirement: Registro e gerenciamento de sessões efêmeras
O Cloudflare Worker em `previa.arestaclimb.com` MUST permitir que instâncias do Aresta Editor registrem e restaurem sessões de prévia identificadas por códigos alfanuméricos de no mínimo 8 caracteres em Base36 (`[0-9a-z]`), garantindo que códigos aleatórios gerados nunca iniciem com o prefixo reservado `pr` e mantendo o estado de conexão ativo e tolerante a reinicializações de container (*cold starts*).

#### Scenario: Registro de nova sessão pelo editor
- **WHEN** o Editor Desktop estabelecer uma conexão com `POST /sessoes` ou conectar diretamente via WebSocket `wss://previa.arestaclimb.com/ws?sessao=<codigo>&token=<jwt>` com token JWT válido
- **THEN** o Worker deve registrar e vincular a sessão ao código informado e ao usuário autenticado, aceitando a conexão WebSocket sem retornar erro 404.

#### Scenario: Registro de nova sessão pelo editor sem colisão com prefixo de PR
- **WHEN** o Editor Desktop solicitar a criação de uma sessão com `POST /sessoes`
- **THEN** o Worker deve gerar um código único de 8 caracteres em Base36 que nunca comece com `"pr"`, registrar a sessão para o usuário autenticado e retornar os metadados da sessão criada

#### Scenario: Rejeição de conexão WebSocket do editor para códigos reservados de PR
- **WHEN** um cliente tentar estabelecer uma conexão WebSocket em `wss://previa.arestaclimb.com/ws?sessao=<codigo>` utilizando um código iniciado pelo prefixo reservado `"pr"`
- **THEN** o Worker deve rejeitar a requisição imediatamente com status HTTP 400 ou 403 sem instanciar um `SessaoDurableObject`

#### Scenario: Auto-restauração de sessão após reinício do Worker
- **WHEN** o Editor Desktop reconectar ao WebSocket `wss://previa.arestaclimb.com/ws?sessao=<codigo>&token=<jwt>` com um código de sessão normal (não iniciado por `"pr"`) e a sessão não estiver presente na memória RAM
- **THEN** o Worker deve validar o token JWT e recriar/restaurar automaticamente a sessão para o código solicitado, mantendo o mesmo identificador acessível para clientes móveis

### Requirement: Roteamento stateless para instâncias de Pull Request
O Cloudflare Worker em `previa.arestaclimb.com` MUST interceptar requisições destinadas a códigos de sessão iniciados pelo prefixo `pr` seguido de dígitos (ex: `pr00-0042`, `pr000042` ou `pr1234567`) e atendê-las de forma 100% *stateless*, sem instanciar `SessaoDurableObject`, buscando os artefatos diretamente em `https://serving.arestaclimb.com/pr/<numero_pr>/`.

#### Scenario: Download de artefatos de croqui de Pull Request pelo aplicativo móvel
- **WHEN** o aplicativo móvel fizer uma requisição `GET https://previa.arestaclimb.com/<codigo_pr>/<caminho_arquivo>` (como `indice.binarypb`, `catalogo.db`, `<id>/compilado.binarypb` ou imagens `.webp`)
- **THEN** o Worker extrai o número inteiro da Pull Request removendo o prefixo `pr` e os zeros à esquerda (ex: `pr00-0042` -> `42`) e retorna a resposta obtida de `https://serving.arestaclimb.com/pr/42/<caminho_arquivo>` preservando cabeçalhos de status, `Content-Type`, `ETag` e CORS

#### Scenario: Consulta de metadados e eventos para código de Pull Request
- **WHEN** um cliente consultar `GET /<codigo_pr>/info` ou `GET /<codigo_pr>/meta`
- **THEN** o Worker responde imediatamente com HTTP 200 e JSON informando o código normalizado sem URL de rede local (`local_url: null`), e retorna HTTP 404 para tentativas de upgrade WebSocket em `/<codigo_pr>/events`

### Requirement: Atendimento do resumo visual HTML e exclusão em Universal Links
O Cloudflare Worker em `previa.arestaclimb.com` MUST servir a página de resumo visual na rota `GET /resumo/<codigo_pr>` e excluir `/resumo/*` da interceptação de Universal Links do iOS.

#### Scenario: Acesso ao resumo visual da Pull Request no navegador
- **WHEN** um usuário acessar `GET https://previa.arestaclimb.com/resumo/<codigo_pr>`
- **THEN** o Worker busca `https://serving.arestaclimb.com/pr/<numero_pr>/resumo.html` e retorna o documento com `Content-Type: text/html; charset=utf-8` (ou uma página HTML 404 amigável caso a Pull Request já tenha sido encerrada/removida)

#### Scenario: Verificação de Universal Links pelo iOS
- **WHEN** o sistema operacional iOS consultar `GET https://previa.arestaclimb.com/.well-known/apple-app-site-association`
- **THEN** o JSON retornado deve conter a diretiva de exclusão para `/resumo/*` (`{ "/": "/resumo/*", "exclude": true }` e `"NOT /resumo/*"`), garantindo que links de resumo abram diretamente no navegador Safari enquanto `/<codigo>` continua abrindo no aplicativo Aresta Climb

### Requirement: Encerramento automático e Batimento Cardíaco
O Cloudflare Worker MUST manter a sessão ativa enquanto o Editor Desktop estiver conectado ou dentro da janela de tolerância de reconexão de 10 minutos, tratando desconexões e inatividade de clientes móveis como ocorrências efêmeras que não encerram a sessão.

#### Scenario: Desconexão temporária do editor com reconexão dentro da tolerância
- **WHEN** o WebSocket do Editor Desktop desconectar momentaneamente e reconectar dentro de até 10 minutos
- **THEN** o Worker deve preservar os dados da sessão e restabelecer o túnel de streaming sem descartar o código de pareamento.

#### Scenario: Desconexão ou ausência de clientes móveis
- **WHEN** nenhum aplicativo móvel estiver conectado ou os clientes móveis fecharem seus WebSockets de eventos
- **THEN** o Worker deve manter a sessão e o túnel do Editor Desktop perfeitamente operacionais, permitindo que novos clientes móveis conectem a qualquer momento pelo mesmo código.

### Requirement: Persistência de metadados no Storage do Durable Object
O Durable Object de sessão MUST salvar o registro essencial de identificação da sessão (`codigo`, `usuarioId`, `criadoEm`, `metadados`) em seu Storage nativo (`state.storage`).

#### Scenario: Recuperação de metadados a partir do storage
- **WHEN** uma requisição de metadados (`GET /<codigo>/info`) ou conexão de eventos (`GET /<codigo>/events`) for recebida e o estado não estiver na memória RAM mas existir no Storage do Durable Object
- **THEN** o Worker deve carregar os metadados do storage e atender à requisição normalmente.
