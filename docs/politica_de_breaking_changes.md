# Política de Breaking Changes

Este documento descreve a arquitetura e os processos necessários para introduzir
mudanças estruturais (breaking changes) no formato de dados do Aresta de forma
segura, sem quebrar o aplicativo para usuários que não atualizaram, e mantendo
uma transição suave.

## Arquitetura de Versionamento

O fluxo de dados entre o `aresta_db` e o aplicativo móvel é estritamente
versionado.

1. **Backend Versionado**: A infraestrutura que serve os arquivos compilados
   (Cloudflare R2 + Cloudflare CDN) suporta múltiplas versões simultâneas
   operando como pastas. Por exemplo, existem os endpoints
   `serving.arestaclimb.com/v14/` e `serving.arestaclimb.com/v15/` operando
   paralelamente.
2. **Nomenclatura (v + Migração)**: A versão consumida pelo app corresponde
   diretamente ao **número da migração** do `aresta_db` onde a quebra de
   compatibilidade ocorreu. Se a migração `15_nova_estrutura.py` quebrar o
   formato Protobuf, a nova versão servida e exigida será `v15`.
3. **App Acoplado à Versão**: Cada binário do aplicativo compilado (release)
   possui o endpoint e a versão dos dados **hardcoded** (embutidos no
   código-fonte). O app na versão da loja 1.2.3 vai sempre buscar dados de
   `v14/`, enquanto a versão 1.3.0 buscará de `v15/`.

### Cache Busting e ETags

Para manter o aplicativo rápido e não gastar banda da CDN à toa:

- **`indice.binarypb`**: O aplicativo utiliza o cabeçalho `If-None-Match`
  passando a `ETag` (fornecida nativamente pelo S3/R2). Se o arquivo não mudou,
  o Cloudflare ou o R2 retornam `304 Not Modified` instantaneamente,
  economizando o download pesado. Quando o arquivo muda, o Cloudflare Edge tem
  seu cache invalidado obrigatoriamente (purge via API do Github Actions no
  momento do deploy).
- **Sub-arquivos (Croquis)**: O `indice.binarypb` contém o hash SHA256 de todos
  os sub-arquivos. O app anexa esse hash na URL ao baixar os croquis (ex:
  `1A.pb?sha256sum=abc`). Se o arquivo mudar, a URL muda, garantindo um "Cache
  Miss" imediato na CDN e contornando caches antigos.

## SharedPreferences e Atualização do Banco

Para garantir que o app não processe dados inconsistentes, o aplicativo salva
localmente a versão do índice e dos dados que ele possui armazenados.

Quando o aplicativo é atualizado via Play Store / App Store, o fluxo de
inicialização segue:

1. O app lê a sua versão "Exigida" (hardcoded no binário, ex: `v15`).
2. O app compara com a versão "Local" (salva no SharedPreferences do celular,
   ex: `v14`).
3. Como `Local < Exigida`, o app **bloqueia a tela inicial**.
4. O app exibe uma tela de carregamento obrigatória ("Atualizando base de
   dados...").
5. Em background, o app faz o download do novo `indice.binarypb` da versão
   `/v15/`.
6. Simultaneamente, o app **re-baixa todos os croquis** que o usuário possuía
   baixados offline (Opção B - Background Update), garantindo que eles também
   migrem para o formato `v15`.
7. O aplicativo trata falhas de rede nesta tela mostrando um aviso claro e um
   botão de "Tentar Novamente", não permitindo acesso ao resto do app até o
   processo terminar com sucesso.
8. Ao concluir, o SharedPreferences é atualizado para `v15` e o app abre
   normalmente.

## Ciclo de Vida de uma Breaking Change

### Passo 1: O Desenvolvimento

O desenvolvedor cria a nova migração no `aresta_db/migrations` que altera a
estrutura final do protobuf gerado. O deploy sempre utiliza o maior número de
versão de migração (parte do nome do arquivo de migração) como sendo a versão
que vai ser deployed. Portanto, ao adicionar uma migração 0015, o próximo deploy
será na pasta `/v15/`. O backend antigo (`/v14/`) permanece intocado e no ar.

### Passo 2: O Lançamento do App

O aplicativo Android/iOS é atualizado. A URL base é alterada para apontar para o
novo endpoint `/v<X>/`.

Vale testar o app aqui para garantir que a tela de bloqueio de migração
funciona, atualizando o índice local e os croquis baixados. Dado que um bug aqui
**bloquearia o uso** do aplicativo pelos usuários, temos que ter certeza que
está tudo certo.

### Passo 3: Remote Config - Recomendação Leve

O app atualizado é enviado para as lojas (Google Play / App Store). No Firebase
Remote Config:

- Sobe-se a chave `recommended_version` para o **Build Number** da nova versão.
- Usuários com a versão antiga verão um banner amigável (que pode ser fechado)
  sugerindo a atualização para usufruir de novos recursos, com um link para a
  loja.

### Passo 4: Remote Config - Bloqueio de Sincronização (Soft Update)

Após um tempo razoável (uma ou duas semanas), queremos começar a aposentar a
infraestrutura ou os dados da versão antiga `/v<X-1>/`. No Firebase Remote
Config:

- Sobe-se a chave `soft_min_version` para o Build Number novo.
- Usuários antigos verão um banner forte, que não pode ser fechado. Eles
  continuam podendo ver seus croquis offline na versão antiga, mas **não
  conseguem baixar novos croquis nem atualizar o índice**. O botão "Atualizar na
  Loja" fica em destaque.

### Passo 5: Remote Config - Bloqueio Total (Hard Update)

Quando a maior parte dos usuários já migrou (após mais uma ou duas semanas), ou
se houver uma urgência de segurança/conteúdo na versão antiga, aciona-se a
alavanca final. No Firebase Remote Config:

- Sobe-se a chave `hard_min_version` para o Build Number novo.
- Usuários antigos perdem completamente o acesso ao aplicativo e veem apenas uma
  tela bloqueando o uso até atualizarem o app.

### Passo 6: Limpeza do Backend

Com o `hard_min_version` aumentado para a versão nova, os arquivos e pastas
referentes à versão `/v<X-1>/` devem ser deletados da infraestrutura do R2 para
cortar custos de armazenamento, encerrando o ciclo da breaking change.

**Processo de Deleção:** A deleção de pastas antigas no Cloudflare R2 **NÃO** é
feita de forma automática por scripts de CI, para evitar apagar acidentalmente
versões ativas. O processo é:

1. O desenvolvedor/mantenedor verifica os acessos a versões antigas no painel do
   **Firebase Analytics** ou **Google Play Console**:
   - **Firebase Analytics**: Acesse os relatórios de eventos (como
     `session_start` ou `screen_view`) e adicione um filtro/comparação por
     `app_version` para visualizar o tráfego da versão antiga.
   - **Google Play Console**: Navegue até "Estatísticas > Dispositivos ativos >
     Por versão do app" para ver o gráfico de adoção.
   - O objetivo é certificar-se de que a curva de usuários ativos nas versões
     antigas atingiu níveis nulos ou irrelevantes (pois o `hard_min_version` já
     forçou a maior parte a atualizar).
2. Utiliza-se um CLI compatível com S3 (como
   `aws s3 rm s3://aresta-bucket/v14/ --recursive`) de uma máquina local
   autorizada para deletar os dados antigos. Prefira usar esse comando a deletar
   a partir do dashboard do Clouflare R2 porque lá pode demorar.
