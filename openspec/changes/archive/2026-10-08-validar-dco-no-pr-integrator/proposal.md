# Proposal

## Why

Atualmente, o workflow do integrador automático (`pr-integrator.yml`) executa o merge do Pull Request utilizando credenciais do GitHub App com privilégios de bypass de branch protection logo após aprovação e geração dos arquivos de deploy. No entanto, o `pr-integrator` não verifica se o status check do DCO (Developer Certificate of Origin) passou com sucesso antes de tentar o merge, permitindo que contribuições sem assinatura válida ou em estado pendente/falho sejam integradas indevidamente.

Além disso, o repositório não possui o arquivo de configuração `.github/dco.yml`, fazendo com que o Probot DCO exija assinatura explícita `Signed-off-by` inclusive para mantenedores e membros da organização ao realizarem edições pontuais diretamente na interface web do GitHub, gerando atrito desnecessário para o time de manutenção.

## What Changes

- **Configuração do DCO para Membros da Organização**: Criação do arquivo de configuração `.github/dco.yml` desativando a exigência de DCO manual para membros da organização (`require.members: false`). Commits realizados diretamente na interface web do GitHub por membros da organização são automaticamente assinados pela chave GPG do GitHub (`verified: true`) e aceitos pelo Probot DCO sem necessidade de cabeçalho `Signed-off-by`.
- **Verificação Obrigatória do Check DCO no Integrador**: Atualização do workflow `.github/workflows/pr-integrator.yml` para consultar os status checks do Pull Request antes de disparar o merge. O workflow aguarda a conclusão da checagem `DCO` e aborta a execução caso ela falhe ou não seja aprovada, impedindo o merge indevido via token com bypass.
- **Resiliência e Feedback no CI**: Inclusão de loop de espera/polling para aguardar a sincronização do check do DCO após o commit automático de deploy do bot, com mensagens de log claras em português reportando o status da verificação.

## Capabilities

### New Capabilities
*(Nenhuma nova capacidade necessária)*

### Modified Capabilities
- `ci-cd-workflow-pr`: Atualização do requisito `Bot Integrator on Pull Request Approval` para exigir que a checagem de DCO esteja aprovada (`SUCCESS` / `pass`) antes de realizar o merge automático do Pull Request.
- `dco-validation`: Atualização da especificação de DCO para contemplar a isenção de membros da organização para commits verificados (como na UI web do GitHub) através da configuração `.github/dco.yml`.

## Impact

- **`.github/dco.yml`**: Novo arquivo de configuração na raiz do repositório para o Probot DCO.
- **`.github/workflows/pr-integrator.yml`**: Step adicional antes de `Realizar Merge do PR` inspecionando o status da checagem `DCO` via GitHub CLI (`gh pr checks`).
- **Nenhum impacto de quebra (breaking change)**: Submissões via Aresta Editor já anexam `Signed-off-by` automaticamente e continuarão passando sem qualquer alteração no código do editor.
