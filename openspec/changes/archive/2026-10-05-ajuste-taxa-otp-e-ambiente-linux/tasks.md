# Tarefas de Implementação

## 1. Configuração de Ambiente Linux e Manifesto Flatpak

- [x] 1.1 Atualizar testes unitários em `editor/plataforma/linux/integracao_test.py` para validar que `configurar_ambiente_plataforma()` define `XKB_LOG_LEVEL="critical"` (TDD - Fase Vermelha)
- [x] 1.2 Implementar a definição de `os.environ.setdefault("XKB_LOG_LEVEL", "critical")` no `AdaptadorLinux.configurar_ambiente_plataforma()` em `editor/plataforma/linux/integracao.py` e verificar aprovação dos testes
- [x] 1.3 Adicionar `--env=XKB_LOG_LEVEL=critical` na lista `finish-args` do manifesto Flatpak em `editor/flatpak/com.arestaclimb.Editor.yaml` e atualizar testes em `tests/manifesto_flatpak_test.py`

## 2. Janela Deslizante de Reenvio de OTP no Editor

- [x] 2.1 Criar testes unitários em `editor/views/tela_de_abertura_test.py` cobrindo o controle de taxa por janela deslizante: permitir até 6 disparos em 60 segundos, bloquear ao atingir a 6ª solicitação exibindo contagem regressiva dinâmica para a vaga mais antiga, e desbloquear quando a janela expirar (TDD - Fase Vermelha)
- [x] 2.2 Implementar a estrutura de histórico de timestamps e o cálculo de tempo de espera dinâmico na `TelaDeAbertura` em `editor/views/tela_de_abertura.py` (TDD - Fase Verde)
- [x] 2.3 Executar a suíte de testes com cobertura (`pytest editor/plataforma/linux editor/views/tela_de_abertura_test.py tests/manifesto_flatpak_test.py --cov`) garantindo 100% de cobertura e ausência de regressões
