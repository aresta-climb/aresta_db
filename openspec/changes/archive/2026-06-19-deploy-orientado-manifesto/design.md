## Context

O ambiente atual de CI (`deploy.yml`) realiza um checkout do Git baixando toda a pasta `generated/` a cada push, que possui aproximadamente 200MB+. O objetivo do pipeline é atualizar o banco de dados que é servido no Cloudflare R2 (um CDN e Object Storage S3-compatible). A atualização hoje é delegada ao `aws s3 sync`. O problema surge na lentidão natural do Git ao baixar blobs binários em massa para cada runner efêmero, aliado ao tempo necessário para o `sync` remoto em baldes que crescerão ao longo do tempo. Há também falhas de purga de cache, gerando comportamentos não determinísticos no mobile app ao baixar versões velhas.

## Goals / Non-Goals

**Goals:**
- Zero downloads no checkout inicial do GitHub Actions.
- Upload atômico focado apenas nos deltas que de fato mudaram através da orquestração de um Manifesto (e não histórico Git).
- Purga estrita no Cloudflare APENAS para os manifestos estruturais (`indice.binarypb` e `arquivos_serving.binarypb`), forçando o cliente a realizar cache-busting nos recursos binários (imagens, compilado) usando querystring.

**Non-Goals:**
- Mudar a arquitetura de acesso de dados no cliente (mobile app continuará chamando a API do S3 da mesmíssima forma).

## Decisions

**1. Criação do `arquivos_serving.binarypb` (Manifesto):**
Para viabilizar comparações rápidas ignorando o Git, adotou-se o modelo de manifesto, idêntico aos frameworks de frontend. O arquivo `deploy_generated.py` listará todos os sha256s do repositório em um arquivo novo (Protobuf `serving.proto`), entregue a cada build.
*Alternativa considerada*: Usar `git diff HEAD~1`. Rejeitado pois depende muito do histórico (ex: squash de commits e branch bumping quebram a lógica).

**2. Script Python Dedicado vs YAML complexo:**
Um script modular em `serving/deploy_serving.py` assumirá o CI. Ele usará `boto3` para puxar o manifesto online atual, compará-lo com o manifesto local que acaba de ser gerado, identificar Adds/Mods/Deletes, e orquestrar.
*Alternativa considerada*: Escrever um mega shell-script no workflow. Rejeitado por falta de testabilidade e segurança no CI.

**3. Lazy Blobs Download (O "Blobless" clone):**
Para evitar puxar os 200MB de arquivos do git localmente no CI, instruímos o Git com `fetch-depth: 0` e `filter: 'blob:none'`. Quando o Python descobre a lista filtrada de X arquivos modificados que o `boto3` precisa mandar pro S3, ele chama via subprocess: `git checkout HEAD -- file1 file2...`, obrigando o Git a puxar só o necessário.
> **Nota sobre Autenticação Git:** O script Python não precisará injetar chaves manualmente no subprocesso. A action padrão `actions/checkout` já configura a autenticação persistente (inserindo um `http.extraheader` com o `GITHUB_TOKEN` no `.git/config`). Portanto, qualquer chamada de CLI nativa do Git feita via Python herdará a autorização para baixar os blobs remotamente, desde que não configuremos `persist-credentials: false` no YAML.

**4. Cache Busting Pelo Cliente e Purga via Python (`update_serving.py`):**
Devido ao limite severo do Cloudflare de 800 URLs/sec, optou-se por uma arquitetura onde purgar o cache envolverá apenas o `indice.binarypb` e o `arquivos_serving.binarypb`. O restante será gerenciado pelo próprio aplicativo cliente via querystring (`?sha256sum=XYZ`). A chamada de Purge à API do Cloudflare ocorrerá diretamente no script Python (utilizando a biblioteca `requests`), garantindo que a invalidação do cache funcione perfeitamente não importa onde o script seja executado (seja no GitHub Actions, ou rodando manualmente na máquina de um desenvolvedor).

**5. Aderência Estrita aos Princípios (TDD e 100% Coverage):**
Seguindo as diretrizes fundamentais do `PRINCIPIOS.md`, a implementação deste módulo Python (`update_serving.py`) nascerá obrigatoriamente sob o regime de **TDD (Test-Driven Development)**. O arquivo `update_serving_test.py` ditará os contratos e cobrirá todos os fluxos lógicos e integrações de fronteira antes da codificação final, garantindo a meta inegociável de **100% de unit test coverage**.

## Risks / Trade-offs

- **[Risco] Fallback Full Deploy:** Quando houver bump da pasta principal (ex: `/v1` para `/v2`), o arquivo `arquivos_serving.binarypb` remoto não será encontrado no R2 (ele estará vazio). O script Python deve lidar com isso graciosamente acionando um `Full Deploy` que baixa 100% da pasta local e faz sync em massa no novo diretório.
- **[Risco] Manutenção do Boto3:** O script agora se vale de dependências próprias. Resolvido com `requirements-serving.txt`.
