# Proposal

## Why

Atualmente, quando uma Pull Request que modifica croquis em `database/` é submetida no GitHub, o workflow `pr-db-validator` compila os croquis apenas em um diretório temporário para verificar erros e descarta os artefatos em seguida. Isso impede que revisores testem imediatamente o croqui experimental no aplicativo móvel Aresta Climb a partir da própria Pull Request e dificulta a revisão visual de mudanças estruturais (vias, graus, traçados de mapas e recortes/máscaras de imagens), que são difíceis de interpretar nos diffs brutos de YAML e Markdown do GitHub.

## What Changes

- **Publicação de Instância Semi-Permanente por Pull Request no R2 (`serving.arestaclimb.com/pr/<id>/`)**:
  - Estender o pipeline de validação de PR (`serving/pr_db_validator.py` e novas bibliotecas modulares em `serving/`) para publicar os artefatos compilados da PR (`indice.binarypb`, `catalogo.db`, `<croqui_id>/compilado.binarypb`, `imagens/*.webp`, `anexos/*`, `thumbnails/<croqui_id>.webp` e `arquivos_serving.yaml`) em uma pasta exclusiva da PR no bucket Cloudflare R2 (`s3://aresta-serving/pr/<numero_pr>/`), preservando também cópias das imagens anteriores modificadas/removidas em `pr/<numero_pr>/_base/` para comparação visual.
  - Adicionar limpeza automática da pasta `pr/<numero_pr>/` no R2 quando a Pull Request for fechada ou mergeada (`pull_request: types: [closed]`), complementada por expiração de ciclo de vida de 30 dias no bucket.
- **Geração de Resumo Estrutural e Visual de Mudanças (`resumo.html` e Comentário Único no Final da PR)**:
  - Criar uma biblioteca de comparação semântica de croquis compilados (pareada pelos `uid` universais das entidades: Picos, Grupos, Setores, Escaladas, Mapas e Pontos de Interesse) e de imagens/anexos contra a branch base (`main`).
  - Gerar uma página autocontida `resumo.html` publicada em `s3://aresta-serving/pr/<numero_pr>/resumo.html` (acessível via `https://previa.arestaclimb.com/resumo/pr00-0042`), contendo:
    - Placar de estatísticas e filtros (`+ Novos`, `~ Modificados`, `- Removidos`);
    - Comparador interativo de mapas com camada vetorial `<svg>` sobreposta às imagens `.webp` (destacando pontos/traçados adicionados em verde, movidos com seta tracejada em amarelo e removidos em vermelho) e modo Lado a Lado / Slider Cortina quando os pixels ou dimensões da imagem do mapa mudarem;
    - Galeria comparativa ("Antes vs. Depois" com Slider e Lado a Lado) para imagens de capa, thumbnails e fotos embutidas em Markdown que foram adicionadas, modificadas ou removidas;
    - Diff campo a campo de escaladas/setores e diff textual de descrições Markdown;
    - Card de conexão rápida com QR Code em SVG inline, código copiável (`pr00-0042`) e botão de abertura direta no aplicativo.
  - Atualizar a estratégia de comentário do bot no GitHub PR para **apagar o comentário anterior do bot** (identificado pela assinatura `<!-- aresta-pr-validator -->`) antes de postar o novo comentário, garantindo que exista apenas 1 comentário ativo e que ele fique **sempre no final da timeline da PR** após o último commit.
- **Esquema de Códigos `pr*` Unbounded (`>= 8` caracteres) e Roteamento Stateless em `previa.arestaclimb.com`**:
  - Definir o formato de código de PR com zero-padding até 6 dígitos para manter 8 caracteres por padrão (`pr00-0042` -> `pr000042`, retrocompatível com versões atuais do app) e tamanho ilimitado (*unbounded*, `>= 8` caracteres) para PRs futuros com mais de 6 dígitos (`pr1234567`).
  - Garantir que o gerador de códigos aleatórios de sessões do Editor Desktop nunca sorteie códigos iniciados pelo prefixo reservado `pr`.
  - No Cloudflare Worker `previa.arestaclimb.com` (`aresta_backend/cloudflare/previa`), interceptar códigos iniciados por `pr` de forma 100% *stateless* (recusando conexões `/ws` e sem instanciar `SessaoDurableObject`), servindo os arquivos de `https://serving.arestaclimb.com/pr/<id>/*` e renderizando `resumo.html` na rota `/resumo/pr*`.
  - Configurar `/.well-known/apple-app-site-association` no Worker para excluir `/resumo/*` (`"exclude": true`), garantindo abertura direta no navegador no iOS.
- **Suporte a Deep Links de Prévia e Sessões de PR no Aplicativo Móvel (`aresta_app`)**:
  - Integrar `previa.arestaclimb.com` e `aresta://previa/*` ao `DeepLinkNavigatorService` no Flutter (aproveitando as configurações nativas já presentes em `AndroidManifest.xml`, `Runner.entitlements` e `Info.plist`) para conectar e abrir o croqui experimental com 1 toque no celular, abrindo rotas `/resumo/*` no navegador externo caso interceptadas no Android.
  - Atualizar `EditorDeCroqui` para aceitar códigos `>= 8` caracteres e não iniciar o loop de reconexão WebSocket de Live Reload (`/events`) quando conectado a uma sessão estática de Pull Request (`pr*`).

## Capabilities

### New Capabilities
- `previa-pull-request`: Compilação e publicação incremental de builds de Pull Requests em `serving.arestaclimb.com/pr/<id>/`, cálculo de diff semântico/visual por UID entre branch base e PR, geração do relatório interativo `resumo.html` (mapas em SVG, sliders de imagens `_base` vs PR, diff de vias/textos) e limpeza de artefatos no encerramento da PR.

### Modified Capabilities
- `ci-cd-workflow-pr`: Atualização do workflow `pr-db-validator` para realizar upload dos artefatos da PR para o Cloudflare R2, substituir o comentário anterior do bot mantendo um único comentário sempre no final da PR com links para o app e para o resumo visual, e remover a pasta `pr/<id>/` do R2 quando a PR for fechada.
- `retransmissor-nuvem-previa`: Roteamento *stateless* (sem Durable Object e sem `/ws`) para códigos com prefixo `pr*` apontando para `serving.arestaclimb.com/pr/<id>/`, atendimento da rota `/resumo/pr*` com `resumo.html`, exclusão de `/resumo/*` no Universal Links do iOS e bloqueio do prefixo `pr` na geração de códigos de sessão aleatórios.
- `cliente-sincronizacao-ao-vivo`: Suporte a códigos de sessão *unbounded* (`>= 8` caracteres Base36) com reserva do prefixo `pr` em `editor/core/codigo_sessao.py` e no cliente mobile, resolução de Deep Links `previa.arestaclimb.com` / `aresta://previa/*` no app e supressão de WebSocket de Live Reload para sessões `pr*`.

## Impact

- **`aresta_db` (Este repositório)**:
  - `editor/core/codigo_sessao.py` e `editor/core/codigo_sessao_test.py`: Suporte a códigos `>= 8` caracteres, formatação/extração de códigos `pr*` e validação de prefixo reservado.
  - `serving/diff_croqui_pr_lib.py` (+ `_test.py`): Nova biblioteca pura para cálculo de diff estrutural (Protobuf por UID), textual (Markdown) e de imagens entre a base e a PR.
  - `serving/renderizador_resumo_pr_lib.py` (+ `_test.py`): Nova biblioteca pura para geração do `resumo.html` interativo (com SVG de mapas, comparadores de imagem e QR Code SVG) e do corpo Markdown do comentário da PR.
  - `serving/publicador_pr_r2_lib.py` (+ `_test.py`) e `serving/cliente_r2_fake.py` (+ `_test.py`): Biblioteca para upload da build e das imagens `_base` para `s3://aresta-serving/pr/<id>/` e remoção em lote no fechamento da PR.
  - `serving/pr_db_validator.py` (+ `_test.py`) e `.github/workflows/pr-db-validator.yml`: Integração do fluxo de publicação, substituição do comentário anterior do bot no final da PR e job de limpeza ao fechar a PR (`closed`).
- **`aresta_backend` (`cloudflare/previa`)**:
  - `src/gerenciador_sessao.ts` e `src/index.ts` (+ `test/worker.test.ts`): Bloqueio de prefixo `pr` em códigos aleatórios, suporte a códigos `>= 8` chars, proxy *stateless* para `serving.arestaclimb.com/pr/<id>/`, rota `/resumo/pr*` e exclusão de `/resumo/*` em `/.well-known/apple-app-site-association`.
- **`aresta_app` (`frontend`)**:
  - `lib/services/editor_croqui.dart`, `lib/navigation/analisador_rotas_deep_link.dart`, `lib/navigation/servico_navegacao_deep_link.dart` e `android/app/src/main/AndroidManifest.xml`: Suporte a códigos `>= 8` chars, supressão de WebSocket `/events` para `pr*` e abertura automática via Deep Link.
