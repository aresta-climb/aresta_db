## Context

O projeto está sendo preparado para adoção open source comunitária. ArestaDB foi concebido para usar GPLv3 para proteger sua base contra usos não autorizados em softwares proprietários, enquanto a Aresta API utilizará Apache 2.0 para ser amplamente integrável sem fricções. O Developer Certificate of Origin (DCO) foi escolhido no lugar de um CLA (Contributor License Agreement) para diminuir a barreira de entrada de novos desenvolvedores, mantendo a responsabilidade legal de cada contribuição clara e justa.

## Goals / Non-Goals

**Goals:**
- Colocar os arquivos de licença corretos (Apache 2.0 para API, GPLv3 para o DB).
- Estabelecer a obrigatoriedade do DCO (`Signed-off-by`) para todas as contribuições, documentado no `CONTRIBUTING.md`.

**Non-Goals:**
- Reescrita do histórico do Git (vamos assumir o histórico atual como limpo e blindado pelo direito autoral exclusivo do mantenedor original).
- Implementação de CLAs pesados ou transferência de Copyright (os autores manterão o copyright de suas próprias contribuições).

## Decisions

- **Localização das Licenças:** A licença GPLv3 será colocada na raiz do repositório atual (`aresta_db`). A licença Apache 2.0 será documentada no componente da API (se separado) ou em pasta específica. Assumiremos neste change a inclusão do `LICENSE` (GPLv3) na raiz do projeto.
- **DCO (Developer Certificate of Origin):** O documento `CONTRIBUTING.md` vai instruir os colaboradores a usarem `git commit -s` para atestar a origem do seu código, seguindo o padrão da Linux Foundation.

## Risks / Trade-offs

- **Trade-off (DCO vs CLA):** Ao adotar o DCO, a organização Aresta perde a flexibilidade de mudar a licença do código do banco de dados unilateralmente no futuro (ex: para vender licenças Enterprise sob código fechado).
  - **Mitigação:** Essa é uma decisão estratégica aceita. O foco de monetização futura do Aresta será em dados premium (croquis fechados), enquanto o motor continuará sendo um bem público.
