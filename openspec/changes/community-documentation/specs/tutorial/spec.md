## ADDED Requirements

### Requirement: Accessible Landing Page
The system SHALL apresentar na raiz do repositório um `README.md` que atue como portal de boas-vindas para o projeto, desprovido de jargões técnicos de infraestrutura em suas seções iniciais.

#### Scenario: A climber visits the repository for the first time
- **WHEN** o usuário não-técnico acessa a página principal do repositório no Github
- **THEN** ele lê instantaneamente a missão colaborativa do projeto e é guiado por um grande call-to-action (ex: "Quer ajudar a catalogar?") direto para a página de tutorial.

### Requirement: Step-by-Step Contribution Guide
The system SHALL fornecer um guia de 4 etapas lineares (`docs/COMO_CONTRIBUIR.md`), munido de linguagem abstraída e imagens estáticas anexadas.

#### Scenario: User reads the contribution flow
- **WHEN** o usuário abre o tutorial de contribuição
- **THEN** ele é instruído linearmente a: (1) Criar conta no GitHub, (2) Baixar o executável oficial (uma única vez), (3) Editar um croqui preenchendo as caixas e (4) Publicar a "Proposta de Alteração" (Pull Request) aguardando curadoria.
