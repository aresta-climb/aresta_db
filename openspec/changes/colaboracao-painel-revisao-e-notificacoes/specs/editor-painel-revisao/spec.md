# editor-painel-revisao Specification

## Purpose
Define a 4ª aba lateral oficial do Editor Aresta ("Revisão"), responsável por exibir os metadados da Pull Request associada a um croqui, a linha do tempo de comentários e permitir a troca de mensagens entre o autor e os mantenedores.

## Requirements

### Requirement: Aba Lateral de Revisão na Janela Principal
A aplicação MUST disponibilizar uma aba lateral com o rótulo "Revisão" e ícone representativo na barra lateral de navegação da `JanelaPrincipal`.

#### Scenario: Visualização da aba no editor
- **WHEN** o usuário abre a `JanelaPrincipal` para editar um croqui
- **THEN** a barra lateral MUST conter o botão de navegação para a aba "Revisão"
- **THEN** clicar no botão MUST transicionar a área central para a `PaginaRevisao`

### Requirement: Exibição de Metadados e Status da Proposta
A `PaginaRevisao` MUST exibir os metadados da sugestão/Pull Request vinculada ao croqui atual com base nas informações salvas no arquivo de metadados local ou obtidas remotamente.

#### Scenario: Croqui com Pull Request aberta
- **GIVEN** que o croqui atual possui uma Pull Request ativa vinculada
- **WHEN** a aba "Revisão" é carregada
- **THEN** a interface MUST exibir o status atual da proposta (`Em Revisão`, `Aprovado` ou `Fechado`), o número da PR, o nome da branch remota e um link para visualização no GitHub

#### Scenario: Croqui local sem submissão
- **GIVEN** que o croqui atual não possui Pull Request vinculada
- **WHEN** a aba "Revisão" é aberta
- **THEN** a interface MUST exibir uma mensagem informativa informando que nenhuma sugestão foi enviada ainda, acompanhada de orientação para submeter alterações pelo botão de submissão

### Requirement: Linha do Tempo e Envio de Comentários
A `PaginaRevisao` MUST exibir a linha do tempo cronológica com todos os comentários trocados no GitHub e disponibilizar um formulário para envio de novas respostas.

#### Scenario: Carregamento dos comentários da PR
- **WHEN** a aba "Revisão" é aberta em um croqui com PR vinculada
- **THEN** o sistema MUST buscar os comentários da Pull Request e exibi-los em ordem cronológica com autor, data/hora e conteúdo

#### Scenario: Envio de novo comentário com sucesso
- **GIVEN** que o usuário digitou uma mensagem no campo de resposta
- **WHEN** o usuário clica no botão "Enviar Comentário"
- **THEN** o sistema MUST enviar a mensagem para a API do GitHub utilizando o token de autenticação da sessão
- **THEN** a linha do tempo MUST ser atualizada imediatamente exibindo o novo comentário postado

### Requirement: Notificação Visual de Mensagens Não Lidas
A interface do Editor MUST exibir um badge numérico no botão da aba "Revisão" indicando a existência de comentários recebidos que ainda não foram visualizados pelo usuário.

#### Scenario: Comentários não lidos presentes
- **GIVEN** que existem novos comentários na PR com identificador superior ao último comentário registrado como lido
- **WHEN** o editor exibe a barra de navegação
- **THEN** o botão da aba "Revisão" MUST exibir um badge numérico destacando a quantidade de mensagens não lidas
- **THEN** ao navegar para a aba "Revisão", o badge MUST ser limpo e o identificador do último comentário atualizado
