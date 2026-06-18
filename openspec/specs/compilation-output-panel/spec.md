## ADDED Requirements

### Requirement: Exibição de saídas de compilação em painel não-bloqueante
O sistema SHALL exibir as mensagens de compilação (erros e avisos) em um componente de painel na parte inferior da interface do editor, sem bloquear o acesso ou edição do restante da aplicação.

#### Scenario: Compilação com erros ou avisos
- **WHEN** o usuário salva o croqui e a rotina de compilação produz mensagens contendo "aviso", "erro", "error" ou "falhou"
- **THEN** o painel inferior deve ser automaticamente exibido/focado e apresentar a lista das mensagens.

#### Scenario: Compilação com sucesso total
- **WHEN** o usuário salva o croqui e a rotina não produz nenhuma mensagem de alerta ou erro
- **THEN** o painel inferior deve ser automaticamente fechado (se estivesse aberto) e o sistema usará a notificação toast verde já existente.

### Requirement: Formatação Rich Text para mensagens
O sistema MUST formatar e colorir o texto de saída baseado em palavras-chave.

#### Scenario: Linha de erro
- **WHEN** uma linha de log contém as palavras "erro", "error" ou "falhou" (case-insensitive)
- **THEN** a linha será exibida num tom vermelho pastel sobre fundo escuro.

#### Scenario: Linha de aviso
- **WHEN** uma linha de log contém a palavra "aviso" (case-insensitive) e não contém as palavras de erro
- **THEN** a linha será exibida num tom amarelo pastel (jamais amarelo intenso/puro) sobre fundo escuro.
