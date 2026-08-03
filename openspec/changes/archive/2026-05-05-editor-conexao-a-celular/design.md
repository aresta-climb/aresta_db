## Contexto

O Editor Aresta precisa de um mecanismo de visualização rápida em dispositivos móveis. Atualmente, os croquis são compilados localmente, mas não há um canal de distribuição imediato para o aplicativo móvel durante a edição experimental. A solução proposta utiliza um servidor web local e QR Codes para facilitar a conexão entre o PC do autor e seu celular.

## Objetivos / Não-Objetivos

**Objetivos:**
- Prover um servidor HTTPS local servindo arquivos estáticos.
- Facilitar o pareamento via QR Code.
- Implementar sincronização automática (auto-save) em 10s de inatividade.
- Feedback visual de estado de conexão.

**Não-Objetivos:**
- Implementar autenticação complexa no servidor local (pareamento por rede local é o modelo de segurança).
- Suportar conexões fora da rede local (sem tunnelamento como ngrok por enquanto).

## Decisões Técnicas

### 1. Servidor HTTP Local
- **Escolha**: `http.server.HTTPServer`.
- **Racional**: Nativo do Python, extremamente simples e evita problemas de certificados auto-assinados em dispositivos móveis.
- **Segurança**: Como o acesso é limitado à rede local e para fins de pré-visualização, o uso de HTTP é justificado pela simplicidade de pareamento.

### 2. Geração de QR Code
- **Escolha**: Biblioteca `qrcode`.
- **Racional**: De facto standard em Python para isso. Gera imagens que podem ser exibidas facilmente em um `QLabel` do PyQt6.
- **Alternativa**: APIs externas de QR Code (descartado por depender de internet).

### 3. Monitoramento de Inatividade (Auto-save)
- **Escolha**: Filtro de eventos do Qt (`QObject.installEventFilter`) instalado no nível da aplicação ou janela principal.
- **Lógica**: Um `QTimer` de 10.000ms. O timer será reiniciado (reset) **apenas** ao detectar eventos de `MouseButtonPress` ou `KeyPress`. 
- **Racional**: Mover o mouse (`MouseMove`) não será considerado interação para fins de auto-save, permitindo que a sincronização ocorra mesmo que o usuário esteja apenas observando a tela. Ao estourar o tempo, dispara a função de salvar e compilar.

### 4. Notificação de Conexão
- **Mecanismo**: O servidor HTTPS enviará um sinal (via `pyqtSignal` ou similar através de um objeto ponte) para a UI quando receber a primeira conexão bem-sucedida. O App Aresta fará uma requisição de "handshake" ou o simples acesso ao `index.json` será contado como conexão.

## Riscos / Trade-offs

- **[Risco] Bloqueio de Firewall** → O Windows pode bloquear a porta do servidor. O manual deve instruir a permitir o acesso.
- **[Risco] Visibilidade na Rede** → O PC e o Celular precisam estar na mesma sub-rede (mesmo Wi-Fi). Se houver isolamento de cliente no roteador, a conexão falhará.
- **[Risco] Colisão de Portas** → Usaremos uma porta alta aleatória, com fallback até ter sucesso, com limite máximo de tentativas.

## Plano de Migração

N/A - Funcionalidade nova e puramente local.
