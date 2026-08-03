## Context

A orquestração do envio de dados à nuvem pelo editor está encapsulada no `PublishController` (`editor/controllers/publish_controller.py`). O método de entrada `iniciar_publicacao` é quem inicia o ritual validando se o croqui está salvo, montando telas e eventualmente rodando as tarefas de build e PR assíncronas. Qualquer nova checagem de estado precisa ocorrer o mais cedo possível neste fluxo para não desperdiçar processamento nem realizar salvamentos indesejados.

## Goals / Non-Goals

**Goals:**
- Instaurar a verificação restrita de versão logo no início da rotina de publicar croquis.
- Manter a UI (User Interface) fluida utilizando abordagens assíncronas padrão (QThread) para realizar chamadas de rede.
- Usar credenciais seguras (Token do usuário) nas chamadas à API, prevenindo o Rate-Limiting.
- Estabelecer o reinício automático programado como forma de "curar" o estado defasado, entregando o bastão do update para a rotina de boot (Fase 3).

**Non-Goals:**
- Implementar as rotinas pesadas de download ou substituição do binário `.exe` dentro do Controller de publicação (a Fase 2 visa apenas ao "Guarda" da porta; o mecanismo complexo de update ficará na Fase 3, que entra em ação no momento em que o app reabre).
- Executar poling na API do Github no modo background intermitente; a requisição deve ser feita estritamente on-demand.

## Decisions

1. **Uso de Worker com QProgressDialog**
   - *Rationale*: O bloqueio do main event loop do Qt em requisições de rede causa lentidão visível e aciona a tela de "Não Respondendo" no Windows.
   - *Abordagem*: Na primeira linha de `iniciar_publicacao`, será levantada uma `QProgressDialog` bloqueante visualmente, e um novo objeto `TarefaChecagemVersao(QThread)` assumirá a requisição HTTP. Conforme o sinal emitido pelo Worker (`versao_ok`, `desatualizado`, ou `erro_rede`), o controller limpa a barra de progresso e dá seguimento à vida ou a interrompe.

2. **Aproveitamento de Token (Rate-Limiting Protection)**
   - *Rationale*: Chamadas públicas à `api.github.com` permitem 60 requisições/hora por IP.
   - *Abordagem*: O Worker receberá em sua inicialização `self.auth.recuperar_token()`, inserindo no Header da requisição, assegurando ampla cota da API associada ao Developer logado.

3. **Diálogo de "Hard Restart"**
   - *Rationale*: O alerta de defasagem precisa dar vazão ao conserto do problema (instalar versão) da forma que as dependências permitam.
   - *Abordagem*: Quando for recebido o sinal `desatualizado`, em vez de um simples "OK" estéril, o diálogo crítico possuirá um botão "Reiniciar Editor". O acionamento deste botão dispara rotinas do SO para recarregar o executável (`subprocess.Popen(sys.executable)` + `QApplication.quit()`), que na próxima execução iniciará o Updater transparente (implementação Fase 3).

## Testing & TDD Strategy (Princípios de Engenharia Aresta)

Para seguir estritamente o `PRINCIPIOS.md`, a execução adotará:
- **Testes de Integração Primeiro**: A fronteira de comunicação entre o `PublishController` e a rotina de checagem deve ter testes formulados logo no início.
- **TDD Rigoroso**: Todos os novos arquivos e lógicas criadas (como o Worker HTTP e funções de reinício) serão acompanhados do seu respectivo `_test.py`. Os testes devem falhar (Red) antes de serem implementados (Green).
- **100% Coverage**: É inegociável possuir 100% de cobertura nos testes unitários das novas linhas introduzidas, mockando devidamente componentes do PyQt, requisições de rede (mock de `requests` ou API interna) e o módulo `subprocess`.
