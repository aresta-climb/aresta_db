## Why

Para transformar o Aresta numa verdadeira comunidade de dados colaborativos. Atualmente, a infraestrutura técnica (GitHub, Pull Requests, Json/Yaml) é uma barreira de entrada intransponível para a esmagadora maioria dos escaladores que desejam compartilhar croquis. Precisamos traduzir o rigor técnico em um tutorial amigável, acolhedor e altamente visual, permitindo que qualquer pessoa, independente do seu conhecimento de programação, seja capaz de instalar o editor e propor novos dados.

## What Changes

- **Refatoração do README.md**: O arquivo principal do repositório deixará de ser apenas um guia técnico e se tornará o "Cartão de Visitas" (Landing Page) do projeto. Ele focará na missão de ser o banco de dados colaborativo de escalada e terá um "Call to Action" claro direcionando para o guia de contribuição.
- **Criação de `docs/COMO_CONTRIBUIR.md`**: Um tutorial passo a passo ensinando o leitor a (1) Criar uma conta gratuita no GitHub, (2) Baixar o editor via `arestaclimb.com/download-editor`, (3) Utilizar a interface do Editor e (4) Publicar a Pull Request (explicada de forma abstrata).
- **Abstração da Pull Request**: Manteremos o nome técnico "Pull Request", mas ele será apresentado conceitualmente como uma "Proposta de Alteração" que entra em uma fila de curadoria.
- **Setup de Assets**: Estabelecimento do diretório `docs/assets/` para abrigar GIFs e screenshots da interface.

## Capabilities

### New Capabilities
- `community-onboarding`: Estrutura de documentação orientada a usuários leigos (não-desenvolvedores), focada em usabilidade e engajamento open-source.

### Modified Capabilities

## Impact

- Redução massiva da curva de aprendizado para novos catalogadores de croquis.
- O repositório ganhará arquivos de imagem estáticos (`/docs/assets/`), devidamente isolados para não poluir o código-fonte.
- Escalabilidade do projeto: com o link de auto-update da Fase 3 enfatizado na documentação, eliminamos o suporte a versões velhas.
