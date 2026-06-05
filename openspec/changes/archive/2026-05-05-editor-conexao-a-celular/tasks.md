## 1. Infraestrutura e Dependências

- [x] 1.1 Adicionar `qrcode` e `pillow` ao arquivo `requirements.txt` do editor.
- [x] 1.2 Implementar testes em `editor/core/servidor_celular_test.py`, seguindo TDD.
- [x] 1.3 Criar biblioteca `editor/core/servidor_celular.py` para gerenciar o servidor HTTP.

## 2. Lógica do Servidor e Conexão

- [x] 2.1 Implementar `ServidorCelular` com suporte a HTTP e sinalização de conexão.
- [x] 2.2 Criar utilitário para obter o endereço IP local da máquina.
- [x] 2.3 Criar utilitário para geração de QR Code em memória (buffer para QPixmap).

## 3. Monitoramento de Inatividade (Auto-save)

- [x] 3.1 Implementar testes em `editor/core/monitor_inatividade_test.py`, seguindo TDD.
- [x] 3.2 Criar biblioteca `editor/core/monitor_inatividade.py` que herda de `QObject`.
- [x] 3.3 Implementar lógica de reset de timer em eventos de input.

## 4. Interface do Usuário (UI)

- [x] 4.1 Implementar testes em `editor/views/dialogo_conexao_celular_test.py`, seguindo TDD.
- [x] 4.2 Criar `editor/views/dialogo_conexao_celular.py`.
- [x] 4.3 Implementar animação circular de "esperando por conexão".
- [x] 4.4 Implementar exibição do QR Code e endereço por extenso.
- [x] 4.5 Atualizar UI para estado "Conectado" dinamicamente.
- [x] 4.6 Implementar sinal para encerramento do servidor via botão.

## 5. Integração na Janela Principal

- [x] 5.1 Implementar testes em `editor/views/area_principal_test.py`, seguindo TDD.
- [x] 5.2 Conectar o botão "Celular" da `JanelaPrincipal` ao novo diálogo.
- [x] 5.3 Implementar lógica de alternância de cores (vermelho/verde) no ícone de celular.
- [x] 5.4 Integrar o ciclo de auto-salvamento quando o servidor estiver ativo.
- [x] 5.5 Garantir o encerramento limpo do servidor ao fechar a aplicação ou diálogo.

## 6. Verificação e Testes de Integração

- [x] 6.1 Realizar bateria completa de testes automatizados.
- [x] 6.2 Validar conformidade com os princípios do projeto (TDD, Library-First, Português).
- [x] 6.3 Atualizar documentação de design se necessário.
- [x] 6.4 Arquivar a mudança usando `/opsx-archive`.
