## Context

O projeto Aresta possui uma arquitetura de licenciamento modular:
- `aresta_db` (motor de processamento, compilador, scripts e editor): originalmente sob GPLv3.
- `aresta_api` (cliente e contratos de API): sob Apache 2.0.
- `database/` (dados estruturados e fatos): sob ODbL 1.0.
- `database/` (textos, croquis históricos e imagens): Copyright reservado dos autores originais.

Como o repositório ainda não recebeu contribuições externas de terceiros via Pull Request, todo o código-fonte atual pertence exclusivamente ao mantenedor principal. Isso viabiliza a migração do motor `aresta_db` para a **Mozilla Public License 2.0 (MPL 2.0)** sem a necessidade de acordos de cessão de direitos ou permissões de múltiplos autores.

## Goals / Non-Goals

**Goals:**
- Substituir o arquivo `LICENSE` na raiz pelo texto oficial e integral da Mozilla Public License 2.0.
- Atualizar todos os cabeçalhos de identificadores de licença SPDX nos arquivos Python (`.py`) e scripts do repositório para `SPDX-License-Identifier: MPL-2.0`.
- Atualizar `LICENCAS_RESUMO.md` e `README.md` com explicações didáticas em português sobre o copyleft a nível de arquivo da MPL 2.0.
- Adicionar ou atualizar testes unitários para garantir conformidade contínua dos cabeçalhos SPDX de licença no código.

**Non-Goals:**
- **Reescrever o histórico do Git**: Não será realizado `git filter-repo` ou `git push --force`. A mudança será efetuada no topo do histórico através de commits normais de transição de licença.
- **Alterar a licença da API (`aresta_api`)**: Permanece sob Apache 2.0.
- **Alterar o licenciamento dos dados (`database/`)**: Metadados continuam sob ODbL 1.0 e corpo editorial/mídias sob Copyright.

## Decisions

### Decisão 1: Relicenciamento no topo do histórico (Novo Commit) vs. Reescrita de Histórico
- **Escolha**: Criar um commit de relicenciamento no branch principal.
- **Justificativa**: Preserva a rastreabilidade e integridade das árvores de objetos do Git, não quebra repositórios clonados ou tags existentes, e segue as melhores práticas da comunidade de software livre.
- **Alternativa descartada**: `git rebase` / `git filter-repo` para forçar histórico antigo. Foi descartada por ser desnecessária juridicamente e arriscada operacionalmente.

### Decisão 2: Padronização do identificador SPDX
- **Escolha**: Usar `# SPDX-License-Identifier: MPL-2.0` na primeira linha de todos os arquivos de código-fonte Python e scripts utilitários do `aresta_db`.
- **Justificativa**: O padrão SPDX é universal, interpretado automaticamente por ferramentas de compliance de licença e pelo ecossistema Open Source.

### Decisão 3: Verificação automatizada via teste
- **Escolha**: Ter um teste unitário (`test_validacao_licencas.py` ou integrado à suíte de build) que varre os arquivos `.py` e valida a presença correta do identificador SPDX `MPL-2.0`.
- **Justificativa**: Previne regressões futuras e garante 100% de cobertura e conformidade segundo os princípios de engenharia do repositório.

## Risks / Trade-offs

- **[Risco] Arquivos esquecidos com menções residuais a GPLv3** → **Mitigação**: Executar uma busca global com script automatizado e validar via teste de integridade que nenhum arquivo `.py` de código mantém `GPL-3.0`.
- **[Risco] Dúvidas de novos colaboradores sobre a abrangência da MPL 2.0** → **Mitigação**: Manter o documento `LICENCAS_RESUMO.md` atualizado com explicações claras sobre o *file-level copyleft* e a independência dos dados (`database/`) e da API (`aresta_api`).
