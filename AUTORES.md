# 👑 Guia para Autores e Mantenedores Originais

Você é o autor de um croqui histórico hospedado no Aresta? Queremos entregar a
você o controle sobre a sua obra!

No Aresta, nós utilizamos o sistema de **CODEOWNERS do GitHub** para garantir
que os autores originais tenham a palavra final sobre qualquer alteração feita
em seu croqui.

## Como funciona o CODEOWNERS?

O GitHub possui um sistema de "Donos de Código" (CODEOWNERS). Quando alguém da
comunidade tenta editar um grau, adicionar uma via nova, ou mudar uma descrição
nos arquivos do **seu** croqui, eles enviam uma "Pull Request" (sugestão de
mudança).

Se você for o Mantenedor Oficial daquele croqui, **o sistema do GitHub bloqueará
a fusão dessa mudança automaticamente e enviará uma notificação diretamente para
você**. A alteração só entrará no banco de dados oficial se **você** revisar e
aprovar!

Exemplo de como registramos isso no sistema:

```text
# Arquivo .github/CODEOWNERS
/database/br_mg_ouro_preto_ouroboulder/ @SeuUsuarioNoGithub
```

## Como reivindicar a manutenção do seu croqui?

É um processo muito rápido. Siga os passos abaixo:

1. **Crie uma conta gratuita no GitHub** (caso ainda não tenha uma).
   - [Como criar?](https://github.com/signup)
2. **Entre em contato conosco:**
   - Abra uma _Issue_ neste repositório com o título "Reivindicação de Autoria
     do croqui <MEU CROQUI>".
   - OU envie um e-mail para `contato@arestaclimb.com` com o mesmo pedido.
3. Na mensagem, informe:
   - Qual é a pasta do seu croqui (ex: `br_mg_ouro_preto_ouroboulder`).
   - O seu nome de usuário do GitHub (ex: `@SeuUsuario`).
   - Uma forma de comprovação de que o material base é seu (um link do seu site,
     blog, fórum, ou o documento original).

Com tudo certo, nossa equipe adicionará o seu usuário imediatamente ao arquivo
oficial `.github/CODEOWNERS` do projeto.

A partir desse momento, você passa a ser o **Revisor Chefe** do seu croqui e a
comunidade precisará do seu selo de aprovação para fazer alterações!

---

## E se eu quiser remover a minha obra do projeto?

O nosso maior objetivo é democratizar o acesso e preservar a história da
escalada, garantindo que o conhecimento não se perca. Por isso, adoraríamos ter
você como parceiro e Mantenedor da sua região!

No entanto, respeitamos profundamente os direitos autorais e o seu desejo como
criador. Se você não deseja de forma alguma que o seu croqui seja preservado e
catalogado gratuitamente no Aresta, nós removeremos o conteúdo sem nenhum
questionamento ou burocracia, mediante a simples confirmação da sua identidade.

👉 **[Consulte a nossa Política de Remoção (Notice and Takedown)](./LICENCAS_RESUMO.md#4-política-de-direitos-autorais-e-remoção-notice-and-takedown)** para ver as opções de contato e solicitar a exclusão da sua obra.
