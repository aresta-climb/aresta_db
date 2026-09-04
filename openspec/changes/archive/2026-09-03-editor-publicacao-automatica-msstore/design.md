## Context

O Editor Aresta já possui seu processo de compilação, testes e empacotamento MSIX automatizado no GitHub Actions (`.github/workflows/release-editor.yml`), e o aplicativo já se encontra oficialmente publicado na Microsoft Store sob o Store ID `9N6CQNH78WN8`. No entanto, a etapa final de submissão no CI/CD estava comentada, exigindo uploads manuais ou impedindo a entrega contínua.

## Goals / Non-Goals

**Goals:**
- Reativar e parametrizar o upload de pacotes `.msix` para a Microsoft Store via `microsoft/microsoft-store-apppublisher` e `msstore-cli`.
- Fornecer controle operacional através da flag `should_publish` (booleano com default `true`), permitindo escolher entre submissão direta para certificação ou envio como rascunho (`--noCommit`).
- Limpar passos legados obsoletos do workflow (como `azure/login` OIDC) que não são utilizados pelo `msstore-cli`.
- Atualizar o identificador canônico de produto em `editor/core/servico_loja.py` de `9NBLGGH4NNS1` (App Installer genérico) para `9N6CQNH78WN8` (Aresta Editor oficial).
- Garantir que a suíte de testes unitários valide a integridade do Store ID canônico e os contratos da biblioteca de loja.

**Non-Goals:**
- Não alterar o processo de empacotamento do MSIX (`makeappx pack`), manifesto ou geração de assets.
- Não implementar gerenciamento complexo de percentuais de rollout gradual nesta fase (o foco é a publicação da versão completa).
- Não criar APIs customizadas de publicação REST fora da CLI oficial recomendada pela Microsoft (`msstore`).

## Decisions

### 1. Suporte à Flag `should_publish` via PowerShell Argument Splatting
- **Decisão**: No step `Publish to MS Store`, montar a lista de argumentos em uma variável de array do PowerShell (`$publishArgs`) e anexar `--noCommit` condicionalmente se `${{ github.event.inputs.should_publish }}` for diferente de `'true'`.
- **Alternativas consideradas**:
  - Dois blocos `if/else` com comandos `msstore publish` duplicados: Duplica os argumentos e aumenta o risco de divergência.
  - Submissão sempre direta: Impede revisões de metadados ou pacotes em ambiente de staging antes da fila de certificação.

### 2. Remoção do Passo `azure/login (OIDC)`
- **Decisão**: Eliminar o passo `Login to Azure (OIDC)` do workflow.
- **Justificativa**: O `msstore reconfigure` utiliza exclusivamente autenticação por Client Secret com o Microsoft Entra ID (`--tenantId`, `--sellerId`, `--clientId`, `--clientSecret`). O `azure/login` autentica o Azure CLI/ARM e adiciona uma dependência de token OIDC que não é consumida pelo `msstore`.

### 3. Atualização do `ID_PRODUTO_PADRAO` em `servico_loja.py`
- **Decisão**: Atualizar a constante de classe `ID_PRODUTO_PADRAO = "9N6CQNH78WN8"` em `editor/core/servico_loja.py`.
- **Justificativa**: Garante que qualquer fallback via deep link (`ms-windows-store://pdp/?ProductId=...`) e a verificação in-app de atualização apontem com exatidão para a página do Editor Aresta na Loja.

## Risks / Trade-offs

- **[Risco] Fila de Certificação Concorrente**: Se o workflow for disparado enquanto uma versão anterior ainda estiver no estado *"In Certification"*, a API da Microsoft rejeitará a nova submissão com erro de conflito.
  - *Mitigação*: Documentar e alertar os operadores de release para aguardarem a conclusão da certificação ativa antes de acionar um novo deploy com `should_publish: true`.
- **[Risco] Polling Demorado no Runner**: Quando executado sem `--noCommit`, o `msstore publish` consulta o status do Partner Center até `CommitStarted`, o que pode consumir alguns minutos do runner.
  - *Mitigação*: A flag `should_publish: false` oferece a válvula de escape caso seja necessário apenas carregar o pacote sem reter o runner.
