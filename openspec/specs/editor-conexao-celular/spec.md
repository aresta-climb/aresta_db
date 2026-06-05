## ADDED Requirements

### Requirement: Servidor HTTP Local para Pré-visualização
O editor SHALL ser capaz de iniciar um servidor HTTP local servindo exclusivamente o conteúdo da pasta `compilado` do croqui atualmente em edição.

#### Scenario: Início do servidor ao abrir conexão
- **WHEN** o usuário clica no botão "Celular" e a conexão não está ativa
- **THEN** o sistema SHALL:
    1. Salvar e compilar o croqui atual
    2. Selecionar uma porta efêmera aleatória disponível (com fallback em caso de colisão)
    3. Iniciar uma thread separada com um servidor HTTP local na porta selecionada
    4. Tornar o servidor acessível na rede local (Wi-Fi)

### Requirement: Diálogo de Instruções de Conexão
O sistema SHALL exibir um diálogo contendo as instruções necessárias para o usuário conectar o aplicativo móvel ao editor.

#### Scenario: Exibição do QR Code e Instruções
- **WHEN** o servidor HTTPS local é iniciado com sucesso
- **THEN** o sistema SHALL abrir um diálogo exibindo:
    1. Instruções passo-a-passo (estar na mesma rede, habilitar modo editor no app)
    2. Um QR Code contendo o endereço IP e porta do servidor
    3. O endereço por extenso logo abaixo do QR Code
    4. Um indicador visual de "esperando por conexão" (ícone animado circular)

### Requirement: Feedback de Status de Conexão
O sistema SHALL fornecer feedback visual imediato quando um dispositivo móvel se conectar ao servidor local.

#### Scenario: Dispositivo conectado com sucesso
- **WHEN** o servidor HTTPS recebe uma requisição/conexão do aplicativo móvel
- **THEN** o diálogo SHALL atualizar seu estado:
    1. Alterar o ícone de carregamento para um "tick" verde grande
    2. Alterar o texto de "esperando por conexão" para "conectado"

### Requirement: Gerenciamento do Ciclo de Vida da Conexão
O usuário SHALL ter controle total sobre o encerramento da conexão e do servidor.

#### Scenario: Encerrar conexão pelo diálogo
- **WHEN** o usuário clica no botão de fechar conexão no diálogo
- **THEN** o sistema SHALL encerrar o servidor HTTPS e fechar o diálogo

#### Scenario: Encerrar conexão pela barra principal
- **WHEN** a conexão está ativa (ícone verde) e o usuário clica no botão "Celular"
- **THEN** o sistema SHALL reabrir o diálogo de conexão permitindo o encerramento
