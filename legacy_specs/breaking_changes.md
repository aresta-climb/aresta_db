Plano para viabilizar breaking changes no indice de croquis

Preciso conseguir fazer uma transição segura dos usuários de uma breaking change
pra outra. Eu pensei no seguinte esquema para a proposta:

O aresta_db já tem versionamento e migrações para breaking changes (na pasta
migrations). Nós podemos oficializar esses números de migração como versões no
backend. Por exemplo, embora atualmente estejamos servindo os croquis apenas de
https://aresta-climb.github.io/aresta_serving, nós podemos criar sub-pastas (v1,
v2, v3, ...) que servem a versão da migração atual. Quando fizermos uma breaking
change, passamos a fazer o deploy na pasta da versão seguinte. A database da
nova versão fica completamente separada da versão anterior.

Aí no aplicativo, salvamos no sharedPreferences a versão atual dos dados do
backend. Quando tem uma breaking change, nós atualizamos o número de versão do
backend embedded no binário para a nova versão, e fazemos as breaking changes no
binário para lidar direito com as breaking changes da database. Publicamos essa
versão, e quando o aplicativo atualizar, vamos ver que a versão compilada é
maior que a versão do sharedPreferences.

Quando isso acontece na abertura (versão compilada > versão no shared
preferences), nós mostramos uma tela de atualização que força o usuário a
esperar o croqui a atualizar com a nova versão da database para realmente abrir
o resto do aplicativo. Desse modo, garantimos que atualizamos para a nova versão
dos dados e não vamos ter uma experiência quebrada do app.

Enquanto os usuários não atualizarem o app, eles vão ficar usando o indice
antigo, que não vai ter atualizações mais mas vai continuar completamente
funcional até eles atualizarem o app. Após a maior parte dos usuários terem
atualizado o seu próprio app, podemos deletar essa versão antiga.

Aí, para ajudar os usuários a atualizarem o app, vamos ter 3 variáveis de
firebase remote config, para níveis diferentes de requisição de atualização:

- recommended_version: se o app do usuário está abaixo dessa versão, mostramos
  um banner leve no topo do app que pode ser fechado sugerindo o usuário a
  atualizar para usufruir de novas funcionalidades, com um link pra app store
  (usaremos isso quando lançarmos uma nova versão do app que tem features novas
  legais!)
- soft_min_version: se o app do usuário está abaixo dessa versão, mostramos um
  banner forte (vermelho por exemplo), que não pode ser fechado, avisando o
  usuário que não vai conseguir atualizar os croquis ou baixar novos croquis
  enquanto não atualizar o app. Porém, croquis já baixados continuarão
  funcionando normalmente. (essa é a versão que usaremos após um tempo razoável
  ter passado depois de uma breaking change, e queremos deletar a versão antiga
  dos dados da database no backend, mas mostrar uma mensagem razoável pro
  usuário).
- hard_min_version: se o app do usuário está abaixo dessa versão, mostramos uma
  tela que completamente bloqueia o aplicativo até o usuário atualizar. (isso
  vai ser pra emergências, tipo a gente estar mostrando algum conteúdo ilegal em
  versões anteriores e precisamos forçar o usuário a atualizar).

Por fim, precisamos de produzir um documento markdown bem detalhado numa pasta
'docs' desse repositório explicando como fazer uma breaking change corretamente
e seguramente, se não vamos esquecer o processo.

Com essas combinações de features (backend em URLs diferentes para breaking
changes diferentes, manter a versão antiga dos dados por um tempo até os
usuários atualizarem pra versão nova, e flags do firebase remote config pra
incentivar ou forçar atualização), acho que temos um sistema robusto para lidar
com breaking changes mesmo que o release dos dados do backend seja completamente
dessincronizado dos releases do app na play store e na app store.

Aqui um mapa visual de como funciona.

```
 [ App Aresta ]                            [ aresta_serving (Backend) ]
                               
┌───────────────────────┐                  ┌──────────────────────────┐
│ Versão App: 1.0       │                  │                          │
│ Versão DB Local: v1   ├───── Consome ───▶│  /v1/indice.json         │
│ (Atualizado)          │                  │  /v1/croquis/...         │
└───────────────────────┘                  │                          │
                                           │                          │
┌───────────────────────┐                  │                          │
│ Versão App: 1.1       │  (Bloqueia tela  │                          │
│ Versão DB Exigida: v2 │   até baixar e   │                          │
│ Versão DB Local: v1   ├─▶ atualizar DB)─▶│  /v2/indice.json         │
└───────────────────────┘                  │  /v2/croquis/...         │
                                           │                          │
┌───────────────────────┐                  │                          │
│ Versão App: 0.9       │ (Firebase Remote │                          │
│ Versão DB Local: v1   │  Config força o  │                          │
│                       │  app a ir pra    │                          │
│                       ├─▶ App Store)     │                          │
└───────────────────────┘                  └──────────────────────────┘
```
