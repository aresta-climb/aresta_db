## Context

Atualmente, o `aresta_db` gera os arquivos compilados em formato Protobuf (índices e croquis na pasta `generated/`) e o processo de deploy os copia diretamente para a raiz do repositório `aresta_serving`. Isso significa que qualquer atualização estrutural nos arquivos Protobuf quebraria aplicativos antigos que esperam o formato antigo, forçando uma atualização imediata do app, o que resulta numa experiência do usuário muito ruim, além de ser inseguro.
Precisamos de um mecanismo que mantenha as versões antigas disponíveis (em subpastas versionadas) e passe a publicar os novos dados em uma nova subpasta correspondente à migração atual.

## Goals / Non-Goals

**Goals:**
- Exportar arquivos gerados em Protobuf para subpastas com o nome `v<numero_da_migracao>`.
- Alterar o pipeline de deploy (Github Actions) para realizar upload (via s3 sync) apenas nas novas subpastas do R2, sem deletar as antigas no bucket.
- Extrair o número da migração atual de forma automática e dinâmica.

**Non-Goals:**
- Modificar a estrutura interna das migrações (já existe).
- Alterar o código do aplicativo (tratado em outra proposta específica para o app).

## Decisions

- **Identificação da Versão**: O Github Actions vai descobrir o número da versão executando o utilitário Python logo no seu primeiro passo e vai guardar essa informação em variáveis de ambiente do workflow (ex: `echo "VERSION=$(python scripts/get_version.py)" >> $GITHUB_ENV`). Todos os próximos passos (upload S3) usarão a variável `${{ env.VERSION }}`.
- **Deploy Incremental com S3 Sync**: Em vez de git push para o `aresta_serving`, o Github Actions usará `aws s3 sync output/ s3://aresta-bucket/v<numero>/`. Isso mapeia perfeitamente porque envia *apenas* os arquivos que mudaram localmente comparado ao que está no R2, economizando tempo extremo nos updates diários.
- **Invalidação de Cache (Purge)**: Após o comando do S3 Sync, o script do Github Actions obrigatoriamente disparará um "Purge Files" na API do Cloudflare mirando única e exclusivamente na URL do `indice.binarypb`, forçando o cache a atualizar globalmente em menos de 1 segundo.

- **Testes e Qualidade (TDD)**: Em total conformidade com o `PRINCIPIOS.md`, a implementação seguirá estritamente TDD (Test-Driven Development). Nenhuma lógica de negócio ou helper (ex: o extrator de número de versão) será desenvolvida sem que antes seus testes unitários sejam escritos e falhem. A cobertura de testes deve ser mantida obrigatoriamente em 100%.

## Risks / Trade-offs

- **[Crescimento do bucket R2]** → O bucket de storage vai acumular dados velhos, aumentando de tamanho. Mitigação: Quando uma versão atingir 0 acessos (via controle de hard_min_version do app), poderemos deletar a pasta antiga manualmente via S3 CLI.
