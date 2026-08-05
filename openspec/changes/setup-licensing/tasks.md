## 1. Licenciamento do Repositório Principal (ArestaDB)

- [x] 1.1 Obter o texto oficial da licença GPLv3
- [x] 1.2 Criar o arquivo `LICENSE` na raiz do repositório `aresta_db` com o conteúdo da GPLv3

## 2. Licenciamento da API (Aresta API)

- [x] 2.1 Criar o arquivo `LICENSE` no diretório correspondente à `aresta_api` (ou na documentação pertinente) com o conteúdo da licença Apache 2.0

## 3. Diretrizes de Contribuição e Documentação Legal (PT-BR)

- [x] 3.1 Criar o arquivo `CONTRIBUTING.md` na raiz do repositório
- [x] 3.2 Adicionar uma seção em "Linguagem Simples" (Plain Language) resumindo as 4 regras do DCO em português
- [x] 3.3 Incluir o texto padrão do DCO em inglês no arquivo `CONTRIBUTING.md` para validade legal
- [x] 3.4 Incluir exemplos práticos de como o desenvolvedor deve assinar seus commits (usando `git commit -s` e dicas para VS Code / IntelliJ)
- [x] 3.5 Criar um arquivo `LICENCAS_RESUMO.md` (ou adicionar ao README) com um FAQ traduzindo as implicações práticas da GPLv3, Apache 2.0 e ODbL/CC-BY-SA

## 4. Automação do DCO no Aresta Editor

- [x] 4.1 Modificar `editor/core/worker.py` para anexar `Signed-off-by:` nas chamadas de `repo.create_commit`
- [x] 4.2 Modificar `editor/core/croqui_experimental.py` para anexar `Signed-off-by:` nos commits automáticos
- [x] 4.3 Modificar a interface de publicação (formulário de Pull Request) para incluir um texto legal informando que publicar implica no aceite do DCO
- [x] 4.4 Atualizar os testes unitários (`worker_test.py` e `croqui_experimental_test.py`) para validar a presença da assinatura nas mensagens de commit

## 5. Validação Automática de DCO no GitHub

- [ ] 5.1 Acessar https://github.com/apps/dco e instalar o app no repositório `aresta_db` (Tarefa manual)
- [ ] 5.2 Configurar regras de proteção de branch (Branch Protection Rules) no GitHub para exigir o status check do DCO antes do merge (Tarefa manual)
