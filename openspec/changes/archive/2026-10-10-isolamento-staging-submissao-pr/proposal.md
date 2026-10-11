# Proposal: Isolamento de Staging e Transparência na Validação de Submissão de PR

## Why

Durante a submissão de sugestões de edição no Aresta Editor, usuários têm enfrentado erros espúrios de rejeição com HTTP 400 (`Violação de segurança: apenas alterações dentro da pasta 'database/' são permitidas. A branch foi removida.`). 
Isso ocorre porque o método `criar_commit_sugestao` serializa todo o índice do repositório local (`index.write_tree()`) sem antes limpá-lo a partir do commit base (`index.read_tree(head_commit.tree_id)`), permitindo que arquivos modificados ou sujos fora de `database/<id_croqui>/` sejam acidentalmente incluídos na árvore do commit. Além disso, a interface do editor descarta a lista de `arquivos_invalidos` enviada pelo servidor, impedindo o diagnóstico claro quando uma violação é reportada.

## What Changes

- **Isolamento Rígido de Staging em `ServicoSubmissao`**:
  - Antes de realizar o `index.add_all([f"database/{id_croqui}"])`, o serviço de submissão carrega explicitamente a árvore limpa do `head_commit` no índice (`index.read_tree(head_commit.tree_id)`), assegurando que nenhum arquivo fora de `database/<id_croqui>/` seja empacotado no commit gerado.
  - Limpeza de arquivos removidos no croqui sincronizados no índice.
- **Transparência e Diagnóstico Detalhado de Erros na Submissão**:
  - `ServicoSubmissao.solicitar_abertura_pr` passa a extrair e incluir a lista de `arquivos_invalidos` no texto do erro gerado, permitindo que a interface gráfica e a telemetria apresentem exatamente quais arquivos violaram o escopo.
- **Enriquecimento do Diálogo de Erro na Interface Gráfica**:
  - `PublishController` e o diálogo de falha exibem a lista formatada de arquivos fora de escopo quando o erro 400 do servidor indicar arquivos inválidos.

## Capabilities

### Modified Capabilities
- `editor-submissao-sugestoes`: Reforçar o isolamento estrito de arquivos no commit assinado com limpeza prévia de árvore no `pygit2.Index` e inclusão de diagnóstico detalhado de arquivos inválidos em falhas de abertura de PR.

## Impact

- **Código Afetado**:
  - `editor/core/servico_submissao.py`: Ajuste no método `criar_commit_sugestao` para inicializar a árvore limpa (`read_tree`) e em `solicitar_abertura_pr` para repassar `arquivos_invalidos`.
  - `editor/controllers/publish_controller.py`: Tratamento de erro detalhado exibindo arquivos inválidos se presentes.
  - Testes unitários e de integração em `editor/core/servico_submissao_test.py` e `editor/controllers/publish_controller_test.py`.
- **APIs e Dependências**: Nenhuma alteração de dependências externas (`pygit2` já suporta `index.read_tree`). Compatível com a Edge Function `create-pr`.
