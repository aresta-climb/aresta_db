## Why

Para preparar o ArestaDB e a Aresta API para serem projetos open source com contribuições da comunidade, é necessário estabelecer formalmente as licenças de código sob as quais eles serão distribuídos, bem como as regras de contribuição. Isso garante proteção legal tanto para o projeto quanto para os usuários, esclarecendo o que pode ou não ser feito com o código.

## What Changes

- Adição da licença **Apache 2.0** para o componente de API, permitindo integrações livres em projetos abertos ou fechados.
- Adição da licença **GPLv3** para o componente `aresta_db`, garantindo que modificações no motor de banco de dados e suas distribuições mantenham-se de código aberto.
- Criação de diretrizes de contribuição (`CONTRIBUTING.md`) exigindo o uso de DCO (Developer Certificate of Origin) via `git commit -s` para todas as contribuições futuras, mantendo a propriedade do código organizada sem a fricção de um CLA pesado.
- Instalação do GitHub App oficial de DCO para validar e auditar automaticamente os Pull Requests da comunidade.
- O Aresta Editor será modificado para injetar automaticamente a assinatura DCO (`Signed-off-by:`) nos commits gerados pelo aplicativo, garantindo conformidade sem fricção para o usuário final.
- Inclusão de um aviso de consentimento legal do DCO na interface de publicação (Pull Request) do Aresta Editor, garantindo validade jurídica à assinatura injetada sem criar fricção (sem pop-ups obstrutivos).
- Criação de documentação legal amigável em português ("Plain Language") para diminuir a barreira de entrada e esclarecer os termos das licenças e do DCO para a comunidade brasileira.
- Não haverá reescrita do histórico do Git, assumindo que não há vazamento de segredos passados no histórico atual.

## Capabilities

### New Capabilities
- `open-source-licenses`: Aplicação e estruturação dos arquivos de licença (Apache 2.0 e GPLv3) e diretrizes de contribuição (DCO).
- `dco-validation`: Configuração da validação automática de DCO via GitHub App para barrar contribuições irregulares.
- `plain-language-legal`: Resumos amigáveis em português (TL;DR) das licenças e do DCO para democratizar o entendimento legal do projeto.

### Modified Capabilities
- `editor-commits`: O editor passará a injetar a assinatura DCO nos commits gerados automatica e programaticamente via `pygit2`.
- `editor-ui`: A tela de PR do editor exibirá um texto de consentimento legal ("Clickwrap") atrelado à ação de publicação, linkando para os resumos em português.

## Impact

- **Código:** Arquivos legais/documentação (`LICENSE`, `CONTRIBUTING.md`, resumos em PT-BR) serão adicionados. Arquivos do backend do editor (`worker.py` e `croqui_experimental.py`) serão levemente alterados para formatar as mensagens de commit, e a interface gráfica de PR receberá um novo `QLabel` com o aviso legal.
- **Ecossistema:** Estabelece a estrutura legal para adoção do banco de dados e da API, e torna o consentimento e adesão ao DCO transparentes, juridicamente válidos e fáceis de entender para a comunidade brasileira.
