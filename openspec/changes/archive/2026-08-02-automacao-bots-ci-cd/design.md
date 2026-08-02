## Context

Com o aumento de contribuidores editando os croquis do banco de dados do Aresta, o processo manual de revisar, compilar, testar e publicar essas alterações cria um gargalo. A automação (CI/CD) visa eliminar a necessidade de testes manuais de compilação por parte do mantenedor e assegurar que a branch `main` nunca seja corrompida por arquivos sintaticamente inválidos. 

## Goals / Non-Goals

**Goals:**
- Garantir que cada Pull Request (PR) passe por uma validação automática que tente compilar um croqui exportável (`.croqui`).
- Bloquear o merge de PRs cuja compilação falhe (validação estrita).
- Prover um mecanismo que, ao receber aprovação humana de revisão (Approval), processe automaticamente os dados para produção (`deploy_generated.py`), fazendo commit no PR e fundindo-o (merge) de volta na `main`.
- Extrair lógicas acopladas ao UI (editor) para bibliotecas Python utilizáveis em modo *headless* por bots.

**Non-Goals:**
- Não realizaremos linting ortográfico ou validação subjetiva do conteúdo dos croquis — apenas a integridade técnica da compilação e esquemas de dados.
- O deploy em si (transferência final para servidores em nuvem, por exemplo) está fora do escopo primário desse documento, apesar do workflow prever o hook para isso no push na `main`.

## Princípios e Padrões (PRINCIPIOS.md)
Seguiremos estritamente os princípios de engenharia do repositório durante a implementação:
- **Tudo em Português:** Nomes de funções, variáveis, docstrings explicativas e testes estarão inteiramente em PT-BR.
- **Library-First:** A lógica de empacotamento *headless* será projetada como uma biblioteca independente, autossuficiente e reutilizável.
- **Testes de Integração e TDD (100% Coverage):** A implementação seguirá TDD (Test-Driven Development). Escreveremos primeiro os testes de integração (como a CLI/Library interage com arquivos reais), seguidos pelos testes unitários. A nova biblioteca de suporte deverá atingir a meta inegociável de 100% de cobertura de código.

## Decisions

- **Isolamento de Workflows:** 
  Separamos o processo em 3 workflows distintos no GitHub Actions: `pr-validator.yml` (focado em feedback rápido a cada commit), `pr-integrator.yml` (assíncrono, focado em fechar e submeter o PR validado) e `deploy.yml` (ponto de extensão para hospedagem no futuro).
- **GitHub App Token no Bot 2:**
  Para evitar conflitos com regras de restrição na `main` (Branch Protection) que geralmente bloqueiam merges de bots ou merges automáticos diretos, o Bot 2 (Integrador) utilizará um **GitHub App Token**. Isso lhe dará privilégio administrativo para forçar o commit dos arquivos gerados e o merge.
- **Uso de `[skip ci]`:**
  O Bot 2 gerará um commit de compilação no PR. Para que esse commit não engatilhe novamente o Bot 1 (criando um loop infinito ou consumo inútil de minutos do Actions), a mensagem de commit gerada pelo bot incluirá a flag `[skip ci]`.
- **Refatoração Headless (`gerar_croqui_experimental.py`):**
  Optamos por criar um script standalone (`scripts/gerar_croqui_experimental.py`) em vez de reaproveitar o ambiente completo do editor, reduzindo dependências pesadas na esteira de CI. Esse script utilizará o `editor.core.croqui_format.empacotar_croqui` para o ZIP e a ofuscação (XOR 0xFF).

## Risks / Trade-offs

- **[Risco] Segurança do Token Privilegiado:** O GitHub App Token concede poder de escrita para contornar proteções.
  *Mitigação:* Será armazenado como GitHub Secret de ambiente, com expiração gerenciada ou escopo mínimo restrito estritamente a PRs.
- **[Risco] Concorrência e Conflitos de Merge:** Se dois PRs passarem por "Approve" simultaneamente, o primeiro Bot 2 a fazer merge na `main` pode causar conflito para o segundo Bot 2 no momento de commitar os gerados na sua respectiva branch.
  *Mitigação:* O repositório deverá usar estratégias como "Require branches to be up to date before merging" no GitHub, forçando o Bot 2 do segundo PR a falhar de forma segura caso a `main` avance. O usuário apenas precisará atualizar o PR com a `main` e dar approve novamente.
