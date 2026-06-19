# Guia de Configuração: Cloudflare R2 e CDN

Para que a arquitetura de "Cache Infinito" com _deploy delta_ funcione
perfeitamente, a infraestrutura da Cloudflare precisa estar corretamente
configurada. Siga os passos abaixo.

## 1. Criação do Bucket R2

1. Acesse o painel da Cloudflare e vá em **R2**.
2. Clique em **Create bucket**.
3. Escolha um nome (ex: `aresta-serving`) e crie o bucket.

## 2. Habilitando a CDN (Custom Domain)

Um bucket R2 sozinho **não possui cache** na borda da Cloudflare. Para que o
cache do CDN funcione e sirva os arquivos de graça, você precisa expor o bucket
em um domínio que você gerencia no Cloudflare (ex: `aresta.app`).

1. Vá nas configurações do seu bucket recém-criado.
2. Navegue até **Settings** > **Public Access** > **Custom Domains**.
3. Conecte um domínio ou subdomínio (ex: `cdn.aresta.app`). O Cloudflare criará
   automaticamente o registro CNAME no seu DNS e ativará o CDN proxy (a nuvem
   laranja) para ele.

## 2.1 Habilitando o Tiered Cache (Mestre de Cache)
Para evitar que dezenas de servidores do Cloudflare espalhados pelo mundo batam no R2 ao mesmo tempo, podemos ligar o **Tiered Cache** (Cache em Camadas). Ele cria "servidores mestres" regionais. Assim, se o Brasil não tiver o arquivo, ele pede para o mestre dos EUA em vez de bater no R2 de novo. Isso economiza requisições no R2 e aumenta monstruosamente a velocidade.

1. No painel do seu domínio (`aresta.app`), vá no menu lateral esquerdo em **Caching** > **Tiered Cache**.
2. Na seção **Tiered Cache Topology**, altere de "Off" para **Smart Tiered Cache** (ou "Generic", dependendo da nomenclatura atual).
3. E pronto! A rede fará o roteamento inteligente de cache sozinha.

## 3. Configuração de Cache Rules (Opcional, mas Recomendado)

Por padrão, o Cloudflare fará o cache dos arquivos baseado na configuração
padrão do seu domínio. No entanto, queremos garantir que nossos `.binarypb`
sejam cacheados ao máximo.

1. Volte à página inicial do seu site (`aresta.app`) no painel do Cloudflare.
2. Vá em **Caching** > **Cache Rules** e clique em **Create Rule**.
3. **Regra de Croquis (Cache Infinito)**:
   - **Expression**: `URI Path contains "/croquis/"`
   - **Cache status**: `Eligible for cache`
   - **Edge TTL**: `Use strict settings` -> `1 year`
   - **Browser TTL**: `1 year`
   - _Isso fará o Cloudflare segurar o arquivo na borda e no celular por 1 ano.
     Como os updates mudam a URL (`?sha256sum=...`), nunca veremos cache velho._
4. O `indice.binarypb` será cacheado normalmente com ETags (comportamento
   nativo).

## 4. Gerando Credenciais para o Github Actions (S3 Sync)

O Github Actions usará a CLI da AWS para fazer upload para o R2.

1. No painel do R2, volte na tela principal e clique em **Manage R2 API
   Tokens**.
2. Clique em **Create API Token**.
3. Nomeie (ex: `Github Actions Deploy`) e dê a permissão **Object Read & Write**
   (restrito ao bucket `aresta-serving`).
4. Após criar, você receberá três informações cruciais. Adicione elas como
   **Secrets** no seu repositório do Github (`aresta_db` > Settings > Secrets
   and variables > Actions):
   - `AWS_ACCESS_KEY_ID` (A Access Key ID)
   - `AWS_SECRET_ACCESS_KEY` (O Secret Access Key)
   - `CLOUDFLARE_ACCOUNT_ID` (O Account ID que aparece na URL de endpoint:
     `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`)

## 5. Gerando Token para Invalidação de Cache (Purge API)

O Github Actions também precisará limpar o cache do `indice.binarypb` toda vez
que finalizar o upload.

1. No Cloudflare, clique no ícone do seu **Perfil** no canto superior direito >
   **My Profile** > **API Tokens**.
2. Clique em **Create Token** > **Create Custom Token**.
3. Nomeie (ex: `Github Actions Cache Purge`).
4. **Permissions**: Selecione `Zone` | `Cache Purge` | `Purge`.
5. **Zone Resources**: Selecione `Include` | `Specific zone` | Selecione seu
   domínio (`aresta.app`).
6. Clique em Continue e gere o token.
7. Adicione este token como um Secret no Github Actions com o nome
   `CLOUDFLARE_API_TOKEN`.

---

### Exemplo de Uso no Github Actions

No `deploy.yml`, seus passos serão similares a este:

```yaml
- name: S3 Sync para R2
  run: aws s3 sync output/ s3://aresta-serving/${{ env.DB_VERSION }}/ --endpoint-url ${{ secrets.CLOUDFLARE_S3_API_URL }}
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.CLOUDFLARE_S3_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.CLOUDFLARE_S3_SECRET_ACCESS_KEY }}
    AWS_REGION: auto

- name: Purge Cache do Indice
  run: |
    curl -X POST "https://api.cloudflare.com/client/v4/zones/${{ secrets.CLOUDFLARE_ZONE_ID }}/purge_cache" \
         -H "Authorization: Bearer ${{ secrets.CLOUDFLARE_CACHE_PURGE_API_TOKEN }}" \
         -H "Content-Type: application/json" \
         --data '{"files":["https://serving.arestaclimb.com/${{ env.DB_VERSION }}/indice.binarypb"]}'
```
