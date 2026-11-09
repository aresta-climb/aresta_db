# Spec Delta

## MODIFIED Requirements

### Requirement: Edição de Arquivos Externos e Nome de Arquivo na UI
O sistema SHALL exibir o componente de nome de arquivo (`CampoFormatoUi.NOME_ARQUIVO`) no topo do formulário para qualquer mensagem correspondente a um arquivo externo (`Setor`, `Grupo`, `ArquivoMarkdown` ou `ArquivoMapas`).
- **Exibição Somente-Leitura e Modificação via Modal**: O campo no formulário SHALL exibir o nome atual do arquivo em modo somente-leitura (`readOnly=True`) acompanhado de um botão `"Modificar..."` que abre um diálogo modal validado para renomeação.
- **Comportamento e Histórico**: A confirmação no modal de renomeação SHALL atualizar `ext_metadados_arquivo.caminho_novo` exclusivamente via comando na pilha de histórico (`QUndoCommand`).
- **Geração Automática Sanitizada**: Para novos elementos ou elementos sem `caminho_novo`/`caminho_original` definido no momento da serialização, o sistema SHALL gerar automaticamente um nome de arquivo sanitizado em `snake_case` ASCII com até `100` caracteres e extensão `.md` (ex: `setor_nome_do_setor.md`, `grupo_nome_do_grupo.md`, `secao_texto_do_botao.md`), utilizando um fallback seguro (`setor.md`, `grupo.md`, `secao.md`, `mapas_gerais.md`) caso o título da entidade possua apenas símbolos.

#### Scenario: Visualização do Campo Nome do Arquivo
- **WHEN** um formulário de um item salvo em arquivo externo é carregado
- **THEN** o sistema SHALL exibir no topo do formulário o nome atual do arquivo em um controle somente-leitura acompanhado do botão `"Modificar..."`.

#### Scenario: Inicialização de Nome para Novo Item
- **WHEN** um novo setor, grupo ou botão textual externo é adicionado à árvore de dados ou serializado sem caminho explícito, mesmo que seu título contenha acentos, espaços ou caracteres especiais (`:`, `"`, `/`, `<`, `>`, etc.)
- **THEN** o sistema SHALL gerar automaticamente um nome de arquivo baseado no tipo e no nome do elemento estritamente em `snake_case` ASCII válido (com até `100` caracteres e extensão `.md`), sem propagar caracteres ilegais para o sistema de arquivos.

#### Scenario: Renomeação de Arquivo via Modal
- **WHEN** o usuário aciona o botão `"Modificar..."`, informa um nome válido em `snake_case` com até `100` caracteres no modal e confirma
- **THEN** o sistema SHALL atualizar `caminho_novo` via histórico de Undo/Redo e refletir o novo nome no formulário.
