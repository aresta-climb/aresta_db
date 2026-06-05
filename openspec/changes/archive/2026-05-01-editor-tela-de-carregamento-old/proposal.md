## Por que

A tela de carregamento atual é apenas visual e não possui as funcionalidades de gerenciamento de croquis conectadas. Para que o editor seja funcional, precisamos permitir que o usuário crie, importe e selecione croquis oficiais para edição, utilizando o formato de croquis experimentais definido anteriormente. Isso possibilita que os autores trabalhem localmente em seus croquis antes de submetê-los ao banco de dados oficial.

## O que muda

- **Conexão do botão "Novo croqui"**: Cria novos projetos com inicialização Git automática.
- **Importação Robusta**: Suporta arquivos `.croqui` com normalização de estrutura (flatten) e resiliência a locks de arquivo no Windows.
- **Edição de Oficiais**: Diálogo de busca performático e cópia assistida com feedback de log em tempo real.
- **UX Avançada**: Histórico ordenado cronologicamente, interface maximizável e responsiva.
- **Integridade**: Mecanismo de limpeza automática (rollback) em caso de falhas operacionais.

## Capacidades

### Novas Capacidades
- `selecao-croqui-oficial`: Diálogo de busca e seleção de croquis existentes no banco de dados oficial (`appdata/aresta_db/database/`).

### Capacidades Modificadas
- `editor-tela-de-carregamento`: Atualização dos requisitos para incluir o comportamento funcional dos botões e da lista.

## Impacto

- `editor/views/tela_de_carregamento.py`: Implementação dos métodos de ação e integração com o core.
- `editor/views/dialogo_busca_croqui.py`: Criação do novo diálogo de busca.
- `editor/core/croqui_experimental.py`: Possíveis melhorias para suportar a criação a partir de um croqui oficial (cópia de arquivos).
