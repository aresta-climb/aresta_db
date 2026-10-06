# Design Técnico

## Contexto

Veja `proposal.md` para a motivação e contexto do problema.
Atualmente, o `AdaptadorLinux.configurar_ambiente_plataforma()` não define variáveis de ambiente antes da inicialização do Qt, permitindo que o `libxkbcommon` cuspa erros de keysym desconhecido (como `dead_hamza`) presentes na tabela Compose padrão do sistema. Além disso, a `TelaDeAbertura` utiliza um temporizador fixo `_segundos_reenvio = 60`, bloqueando qualquer reenvio subsequente por um minuto inteiro.

## Objetivos e Não-Objetivos

**Objetivos:**
- Silenciar avisos e erros diagnósticos não-fatais do `libxkbcommon` no Linux tanto nativamente quanto no sandbox Flatpak.
- Implementar controle de taxa baseado em janela móvel deslizante (*sliding window*) de 6 solicitações por 60 segundos na interface da `TelaDeAbertura`.
- Exibir contagem regressiva precisa para a liberação da vaga mais antiga quando o limite da janela deslizante for atingido.
- Adicionar debouncing de segurança (mínimo de 3 segundos) entre disparos consecutivos para impedir rajadas acidentais por duplo clique.
- Garantir 100% de cobertura de testes unitários para todas as rotinas alteradas.

**Não-Objetivos:**
- Alterar as configurações de infraestrutura ou API do Supabase Auth remotamente (o Supabase já suporta 30 req/5min).
- Modificar o fluxo de validação de tokens JWT ou do diálogo de perfil do autor.

## Decisões Técnicas

### 1. Injeção de `XKB_LOG_LEVEL=critical`
- **Decisão:** Injetar `XKB_LOG_LEVEL=critical` via `os.environ.setdefault()` no `AdaptadorLinux.configurar_ambiente_plataforma()` e declarar `--env=XKB_LOG_LEVEL=critical` nos `finish-args` do Flatpak (`com.arestaclimb.Editor.yaml`).
- **Alternativas consideradas:**
  - *Filtrar stderr via redirecionamento de descritores no PyInstaller:* Rejeitada por fragilidade e risco de ocultar exceções reais de Python.
  - *Atualizar o runtime Flatpak para KDE 6.8+:* Válida como melhoria futura, mas não resolve o caso de execução nativa do desenvolvedor em distros com compose mais recente.
  - *setdefault no AdaptadorLinux:* Solução limpa, nativa, suportada pelo próprio `libxkbcommon` e executada antes da inicialização de qualquer janela Qt.

### 2. Algoritmo de Janela Deslizante de OTP
- **Decisão:** Manter uma lista em memória de timestamps (`list[float]`) na `TelaDeAbertura` representando os envios recentes.
  - Ao avaliar o reenvio:
    1. Remove todos os timestamps com idade superior a 60 segundos em relação ao `time.time()`.
    2. Se `len(timestamps) < 6`: o envio é permitido.
    3. Se `len(timestamps) >= 6`: o botão fica desabilitado, e o tempo restante até a expiração do timestamp mais antigo (`60 - (agora - timestamps[0])`) é exibido e decrementado pelo `QTimer`.
    4. Um pequeno intervalo mínimo de resfriamento (3 segundos) é aplicado logo após cada envio para impedir múltiplos cliques instantâneos enquanto a requisição de rede está trafegando.
- **Alternativas consideradas:**
  - *Temporizador fixo de 10s ou 20s:* Mais simples, porém não permite que o usuário faça 2 ou 3 tentativas rápidas caso o e-mail não chegue de imediato. A janela deslizante entrega a máxima flexibilidade respeitando estritamente o teto de 6 por minuto.

## Riscos e Mitigações

- **[Risco]** Relógio do sistema dessincronizado ou com saltos temporais.
  - *Mitigação:* Usar `time.monotonic()` ou tolerância segura na checagem dos timestamps.
- **[Risco]** Usuário fechar e reabrir a janela splash para tentar resetar a cota local.
  - *Mitigação:* Como o Supabase possui seu próprio rate limit (30 req / 5 min), qualquer tentativa abusiva externa ainda será protegida pelo backend com o erro 429 já traduzido pelo `ClienteAuthSupabase`.
