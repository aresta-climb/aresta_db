## 1. Testes Iniciais (TDD e Integração)

- [x] 1.1 Criar teste de integração em `editor/views/tela_de_carregamento_test.py` que simule o clique em "Novo croqui", o preenchimento do diálogo e a verificação da criação do arquivo `croqui.yaml`.
- [x] 1.2 Criar testes unitários para a lógica de normalização e geração automática do ID do croqui.

## 2. Implementação da Interface (UI)

- [x] 2.1 Implementar a classe `DialogoNovoCroqui` em `editor/views/tela_de_carregamento.py` com os campos: Nome do Pico, Cidade, Estado, País e ID (somente leitura).
- [x] 2.2 Implementar a reatividade dos campos para que o ID seja atualizado automaticamente enquanto o usuário digita, incluindo o indicador visual de disponibilidade (tick verde / "X" vermelho).
- [x] 2.3 Implementar a lógica de bloqueio do botão de confirmação e exibição de mensagem de erro caso o ID já exista ou os campos obrigatórios estejam vazios.


## 3. Lógica de Criação e Compilação

- [x] 3.1 Implementar a função utilitária de geração de ID (normalização, remoção de acentos, camelCase).
- [x] 3.2 Implementar o serviço de criação da estrutura inicial: pasta do croqui e arquivo `croqui.yaml` seguindo a estrutura da mensagem `Croqui` do `croqui.proto`.

- [x] 3.3 Integrar o disparo da compilação inicial e exibição do progresso no `DialogoProgressoLog`.

## 4. Verificação Final

- [x] 4.1 Garantir que todos os testes (`pytest`) estejam passando.
- [x] 4.2 Realizar teste manual: criar um croqui de teste e verificar se ele abre para edição e se o arquivo compilado foi gerado com sucesso.

