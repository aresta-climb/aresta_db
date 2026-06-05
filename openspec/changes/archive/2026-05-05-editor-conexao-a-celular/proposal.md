## Por Que

Atualmente, os autores que editam croquis experimentais no Aresta Editor não têm uma forma simples de visualizar as alterações em tempo real no aplicativo Aresta em seus dispositivos móveis. A conexão a celular permite que o autor visualize o croqui que está editando diretamente no dispositivo físico, garantindo que a renderização e os mapas estejam corretos antes da publicação oficial.

## O Que Muda

- Implementação de um servidor HTTP local que serve a pasta 'compilado' do croqui atual.
- Adição de um diálogo de conexão no editor com instruções e QR Code.
- Integração de um ciclo de salvamento e compilação automática (auto-save/auto-compile) quando o celular está conectado.
- Atualização visual do ícone de celular na barra superior para indicar o estado da conexão.
- Interface de feedback de conexão em tempo real (esperando conexão vs. conectado).

## Capacidades

### Novas Capacidades
- `editor-conexao-celular`: Gerenciamento do servidor HTTP local, geração de QR Code e protocolo de conexão com o aplicativo móvel.
- `editor-auto-salvamento-experimental`: Lógica de monitoramento de inatividade e disparo automático de salvamento/compilação para sincronização com o celular.

### Capacidades Modificadas
- `editor-area-principal`: Integração do botão de celular com o novo fluxo de conexão e estados visuais.

## Impacto

- **UI**: Nova Janela de Diálogo (Dialog) e atualizações na Janela Principal.
- **Core**: Novo módulo para o servidor HTTP e gerenciamento de threads de background.
- **Segurança**: Uso de HTTP local na rede Wi-Fi do usuário.
- **UX**: Fluxo de auto-save que pode interferir na edição se não for bem implementado (necessário debouncing de 10s).
