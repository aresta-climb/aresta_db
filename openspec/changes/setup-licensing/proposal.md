## Why

Para preparar o ArestaDB e a Aresta API para serem projetos open source com contribuições da comunidade, é necessário estabelecer formalmente as licenças de código sob as quais eles serão distribuídos, bem como as regras de contribuição. Isso garante proteção legal tanto para o projeto quanto para os usuários, esclarecendo o que pode ou não ser feito com o código.

## What Changes

- Adição da licença **Apache 2.0** para o componente de API, permitindo integrações livres em projetos abertos ou fechados.
- Adição da licença **GPLv3** para o componente `aresta_db`, garantindo que modificações no motor de banco de dados e suas distribuições mantenham-se de código aberto.
- Criação de diretrizes de contribuição (`CONTRIBUTING.md`) exigindo o uso de DCO (Developer Certificate of Origin) via `git commit -s` para todas as contribuições futuras, mantendo a propriedade do código organizada sem a fricção de um CLA pesado.
- Não haverá reescrita do histórico do Git, assumindo que não há vazamento de segredos passados no histórico atual.

## Capabilities

### New Capabilities
- `open-source-licenses`: Aplicação e estruturação dos arquivos de licença (Apache 2.0 e GPLv3) e diretrizes de contribuição (DCO).

### Modified Capabilities
<!-- Nenhuma funcionalidade técnica está sendo modificada -->

## Impact

- **Código:** Nenhum código funcional será alterado. Apenas arquivos legais/documentação (`LICENSE`, `CONTRIBUTING.md`) serão adicionados.
- **Ecossistema:** Estabelece a estrutura legal para adoção do banco de dados e da API, além de definir o fluxo de trabalho (DCO) para novos desenvolvedores.
