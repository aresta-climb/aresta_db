## 1. Biblioteca de Códigos de Sessão (`codigo_sessao.py`)

- [ ] 1.1 (TDD - Vermelho) Escrever testes unitários em `editor/core/codigo_sessao_test.py` cobrindo geração de código Base36 de 8 caracteres, formatação com hífen (`k9x2-p83a`), validação de caracteres válidos e normalização de entrada (remoção de hifens e conversão para minúsculas).
- [ ] 1.2 (TDD - Verde) Implementar a biblioteca isolada `editor/core/codigo_sessao.py` com funções puras (`gerar_codigo_sessao`, `formatar_codigo`, `validar_codigo`, `normalizar_codigo`).
- [ ] 1.3 (TDD - Refatorar) Garantir 100% de cobertura de testes unitários e conformidade de tipos na biblioteca `codigo_sessao.py`.

## 2. Retransmissor na Nuvem Cloudflare (`previa.arestaclimb.com`)

- [ ] 2.1 (TDD - Vermelho) Escrever testes de integração para o Cloudflare Worker cobrindo o fluxo de registro de sessão WebSocket, consulta de metadados locais (`GET /<codigo>/info`), proxy reverso de streaming e encerramento automático por batimento cardíaco.
- [ ] 2.2 (TDD - Verde) Configurar a estrutura do projeto do Cloudflare Worker (`wrangler.jsonc` e TypeScript).
- [ ] 2.3 (TDD - Verde) Implementar o gerenciador de sessões efêmeras em memória RAM utilizando a WebSocket Hibernation API.
- [ ] 2.4 (TDD - Verde) Implementar o endpoint de consulta de metadados de rede local (`GET /<codigo>/info` ou `GET /<codigo>/handshake`).
- [ ] 2.5 (TDD - Verde) Implementar o proxy reverso de streaming HTTP-para-WebSocket com repasse de requisições de arquivos e transmissão de cabeçalhos.
- [ ] 2.6 (TDD - Verde) Implementar verificação periódica de batimentos cardíacos (ping/pong a cada 30 segundos) e tempo limite de inatividade (20-30 min).
- [ ] 2.7 (TDD - Refatorar) Garantir 100% de cobertura de testes automatizados no worker.

## 3. Biblioteca do Túnel de Retransmissão (`tunel_retransmissor.py`)

- [ ] 3.1 (TDD - Vermelho) Escrever testes de integração e unitários em `editor/core/tunel_retransmissor_test.py` simulando conexão WebSocket com o retransmissor, anúncio de IP/porta, processamento de requisição de arquivo estático da pasta compilada e desconexão graciosa.
- [ ] 3.2 (TDD - Verde) Implementar a biblioteca modular `editor/core/tunel_retransmissor.py` gerenciando o cliente WebSocket de saída assíncrono para `wss://previa.arestaclimb.com/ws`.
- [ ] 3.3 (TDD - Verde) Implementar envio de metadados locais (IP e porta) e manipulador de leitura de arquivos compilados em disco com envio de chunks binários pelo socket.
- [ ] 3.4 (TDD - Verde) Implementar emissão de eventos push de recarregamento em tempo real (`{"tipo": "recarregar", "setor": "<id>"}`).
- [ ] 3.5 (TDD - Refatorar) Integrar `tunel_retransmissor.py` ao `servidor_celular.py` mantendo desacoplamento e garantindo 100% de cobertura de testes.

## 4. Interface do Usuário do Editor Desktop (`aresta_db`)

- [ ] 4.1 (TDD - Vermelho) Escrever testes de interface em `editor/legacy_views/dialogo_conexao_celular_test.py` verificando a renderização do link canônico `previa.arestaclimb.com/<codigo>`, código formatado (`k9x2-p83a`), QR Code e alternância de indicadores visuais de conexão ativa (Local vs Retransmissor).
- [ ] 4.2 (TDD - Verde) Atualizar `DialogoConexaoCelular` para incorporar o gerador de código, a nova URL limpa e os indicadores visuais de estado da conexão.
- [ ] 4.3 (TDD - Refatorar) Refatorar a UI garantindo que toda mutação de estado de sessão obedeça aos padrões declarativos do PyQt6 sem efeitos colaterais.

## 5. Aplicativo Móvel (`aresta_app`) - Resolução Híbrida e Sincronização

- [ ] 5.1 (TDD - Vermelho) Escrever testes unitários e de integração no Flutter (`test/services/editor_croqui_test.dart`) cobrindo a normalização de código manual, disputa de rede em paralelo (LAN vs Retransmissor) e escuta de eventos WebSocket de recarregamento.
- [ ] 5.2 (TDD - Verde) Implementar a resolução híbrida no serviço `EditorDeCroqui` (consulta ao retransmissor e teste da rede local com tempo limite).
- [ ] 5.3 (TDD - Verde) Implementar a tela de conexão com campo de digitação manual do código de 8 caracteres e normalização automática.
- [ ] 5.4 (TDD - Verde) Configurar captura de links diretos (`https://previa.arestaclimb.com/*`) direcionando para o modo de revisão do aplicativo.
- [ ] 5.5 (TDD - Verde) Implementar o cliente de eventos WebSocket no Flutter para invalidação automática de cache e recarregamento reativo do croqui na tela.
- [ ] 5.6 (TDD - Refatorar) Garantir 100% de cobertura de testes no Flutter para todos os novos fluxos.
