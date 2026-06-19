## Why

O aplicativo mobile precisa lidar de forma segura com *breaking changes* na estrutura de dados dos croquis. Para isso, precisamos que o backend suporte servir múltiplas versões dos dados simultaneamente. Esta proposta adequa os scripts de exportação e de deploy do `aresta_db` para gerar os dados em pastas versionadas (ex: `/v14/`), atrelando a versão dos dados diretamente ao número da migração correspondente.

## What Changes

- O sistema de exportação (build/exportação de arquivos binários Protobuf na pasta `generated/`) passará a gerar os arquivos dentro de uma subpasta com a versão atual da base de dados (ex: `vX`, onde X é o número da migração mais recente).
- Os scripts de deploy/CI (Github Actions) serão ajustados para realizar o upload (via `aws s3 sync`) dos arquivos compilados diretamente para o bucket Cloudflare R2 na subpasta da versão correspondente, abandonando a antiga publicação via repositório Git (`aresta_serving`) e preservando as versões antigas.

## Capabilities

### New Capabilities
- `backend-versioning`: Suporte a exportação de dados e deploy para pastas versionadas baseadas no número da migração.

### Modified Capabilities
- 

## Impact

- `build.py` ou scripts de exportação relacionados.
- Workflows do Github Actions (`.github/workflows/deploy.yml` ou similar).
- O repositório `aresta_serving` será congelado e eventualmente desativado, sendo substituído inteiramente pelo bucket R2 e Cloudflare CDN.
