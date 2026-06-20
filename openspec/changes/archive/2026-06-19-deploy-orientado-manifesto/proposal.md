## Why

O processo atual de deploy para o Cloudflare R2 no GitHub Actions faz o download completo de toda a pasta `generated/` a cada commit via checkout do git e delega a comparação para o `aws s3 sync`. Como o banco tende a crescer bastante, baixar 200MB+ de blobs no Action apenas para sincronizar 1MB de atualizações gasta banda e tempo de execução. Com a adoção do deploy orientado a manifesto, tornamos a sincronização muito mais leve, idempotente, e transferimos o controle lógico de bash não-testado no `.yml` para um script em Python totalmente testável.

## What Changes

- Geração automatizada do `arquivos_serving.binarypb` (Manifesto).
- Implementação de um script Python (`update_serving.py`) rodando via GitHub Actions que avalia o delta comparando o manifesto local com o manifesto online.
- Comando `git checkout HEAD -- <arquivos>` para fazer download pontual e otimizado via Blobless Clone no GitHub Actions.
- Invalidação cirúrgica de cache do Cloudflare focada exclusivamente nos manifestos (`indice` e `arquivos_serving`).
- Transição do script antigo de deploy Bash para o script modular em Python usando `boto3`.

## Capabilities

### New Capabilities
- `deploy-manifest-sync`: Capacidade de orquestrar downloads parciais no repositório de dados (Blobless) e sincronizar precisamente com o object storage.
- `cache-invalidation-minimal`: Invalidação cirúrgica de cache restrita aos manifestos, empurrando o cache busting para o cliente via query string.

### Modified Capabilities
- (Nenhuma alteração nos requisitos de capacidades existentes)

## Impact

- **CI/CD Pipeline**: O script `.github/workflows/deploy.yml` sofre refatoração drástica, ficando bem mais rápido, eficiente e minimalista.
- **Ecossistema do Projeto**: Novas dependências para CI (`boto3`, `requests`) isoladas via `requirements-serving.txt`.
- **R2 Storage**: Arquivos no Cloudflare R2 e as diretrizes de versionamento (`v1/`, `v2/`) permanecem inalteradas, mas as chamadas de modificação se dão de forma explícita.
