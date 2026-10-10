# Tasks

## 1. Isolamento de Staging em ServicoSubmissao

- [ ] 1.1 Criar testes unitários em `editor/core/servico_submissao_test.py` simulando arquivos sujos fora de `database/<id_croqui>/` no repositório base e arquivos deletados dentro do croqui, verificando a árvore do commit gerado por `criar_commit_sugestao`
- [ ] 1.2 Atualizar `criar_commit_sugestao` em `editor/core/servico_submissao.py` para carregar a árvore base limpa via `index.read_tree(head_commit.tree_id)` e remover do índice arquivos excluídos da pasta do croqui, verificando a passagem dos testes

## 2. Transparência de Erros e Arquivos Inválidos

- [ ] 2.1 Criar testes unitários em `editor/core/servico_submissao_test.py` para `solicitar_abertura_pr` validando a extração do campo `arquivos_invalidos` e a composição de mensagem clara em respostas de erro HTTP 400
- [ ] 2.2 Atualizar `solicitar_abertura_pr` em `editor/core/servico_submissao.py` para extrair `arquivos_invalidos` da resposta JSON e formatar a mensagem detalhada da exceção `ErroSubmissao`, verificando a passagem dos testes

## 3. Apresentação na Interface Gráfica

- [ ] 3.1 Criar testes unitários em `editor/controllers/publish_controller_test.py` verificando que a mensagem enriquecida com a lista de arquivos inválidos é exibida ao usuário no diálogo de erro
- [ ] 3.2 Ajustar o tratamento de exibição de erro em `editor/controllers/publish_controller.py` para formatar adequadamente quebras de linha e itens de arquivos fora de escopo, verificando a passagem dos testes

## 4. Verificação de Cobertura e Integridade

- [ ] 4.1 Executar a suíte de testes completa com medição de cobertura (`pytest --cov`) para assegurar 100% de cobertura nos arquivos modificados
