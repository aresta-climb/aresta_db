## ADDED Requirements

### Requirement: Apresentação de Erro no Salvamento com Diálogo Estruturado
Quando o salvamento do croqui falhar durante a persistência em disco ou compilação, a Área Principal SHALL delegar a apresentação para a biblioteca `dialogo_erro_salvamento`, exibindo uma caixa de diálogo informativa estruturada orientando o usuário com linguagem clara e ocultando detalhes técnicos em seção expansível com recurso de cópia.

#### Scenario: Exibição de erro com detalhes técnicos expansíveis
- **WHEN** a tarefa de salvamento emitir falha (`_on_salvar_erro`)
- **THEN** o sistema SHALL exibir uma caixa de diálogo modal com:
    1. Mensagem principal limpa informando que não foi possível concluir o salvamento
    2. Texto explicativo orientando o usuário de que seus dados em tela permanecem seguros
    3. Área de detalhes técnicos acessível através de botão expansível nativo ("Mostrar Detalhes"), contendo o rastreamento completo e registros do compilador
    4. Botão de ação rápida para copiar o conteúdo dos detalhes técnicos para a área de transferência do sistema operacional.

#### Scenario: Mensagem sem atribuição indevida a estruturas em progresso
- **WHEN** ocorrer um erro de compilação durante o salvamento
- **THEN** a mensagem principal e orientativa da caixa de diálogo não SHALL culpar a existência de picos, grupos ou setores vazios ou incompletos, tratando estruturas em progresso como estados normais do editor.
