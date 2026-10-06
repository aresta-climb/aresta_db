# Proposta

## Motivação (Why)

Ao executar o Editor Aresta no Linux (tanto via Flatpak quanto nativamente), a biblioteca `libxkbcommon` emite avisos recorrentes no terminal sobre o keysym `dead_hamza` não reconhecido nas tabelas Compose do sistema, poluindo os logs e causando falsos alertas de falha aos usuários. Além disso, a tela de autenticação do editor impõe um bloqueio rígido de 60 segundos após cada solicitação de código OTP por e-mail, gerando fricção desnecessária para usuários que precisam reenviar o código, descompassando-se da política do servidor Supabase Auth que comporta até 30 requisições a cada 5 minutos.

## O Que Muda (What Changes)

- **Configuração de Ambiente Linux:** Injeção automática da variável de ambiente `XKB_LOG_LEVEL=critical` no adaptador Linux (`AdaptadorLinux.configurar_ambiente_plataforma`) e no manifesto Flatpak (`com.arestaclimb.Editor.yaml`), silenciando avisos não-críticos de parse do `libxkbcommon`.
- **Janela Deslizante de OTP na Interface:** Substituição do temporizador rígido de 60 segundos na tela de abertura (`TelaDeAbertura`) por uma janela deslizante inteligente que permite até 6 envios a cada minuto (60 segundos).
- **Contagem Regressiva Dinâmica:** Quando a cota de 6 envios por minuto for atingida, o botão de reenvio bloqueia temporariamente informando os segundos exatos até a liberação da vaga mais antiga da janela.

## Capacidades (Capabilities)

### Novas Capacidades
<!-- Nenhuma nova capacidade introduzida nesta mudança. -->

### Capacidades Modificadas
- `editor-autenticacao`: Atualiza os requisitos de fluxo de reenvio do código de acesso OTP na interface, adotando a janela deslizante de 6 envios por minuto em vez do temporizador rígido de 60 segundos.
- `editor-distribuicao-linux`: Atualiza as exigências de ambiente de execução no Linux e manifesto Flatpak para suprimir mensagens não-críticas do subsistema gráfico e de teclado (`libxkbcommon`).

## Impacto (Impact)

- **Código Afetado:**
  - `editor/plataforma/linux/integracao.py`
  - `editor/flatpak/com.arestaclimb.Editor.yaml`
  - `editor/views/tela_de_abertura.py`
- **Testes Unitários:**
  - `editor/plataforma/linux/integracao_test.py`
  - `editor/views/tela_de_abertura_test.py`
  - `tests/manifesto_flatpak_test.py`
- **APIs/Dependências Externas:** Nenhuma nova dependência; utiliza `os.environ` e a biblioteca padrão do Python juntamente com PySide6.
