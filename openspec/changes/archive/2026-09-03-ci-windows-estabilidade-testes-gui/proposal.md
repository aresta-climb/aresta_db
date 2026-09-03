## Why

Durante o fluxo de lançamento no GitHub Actions (
elease-editor.yml), a execução da suíte de testes congelava a exatamente 97% (1.224 de 1.252 testes concluídos), estourando o tempo limite de 10 minutos da etapa sem relatar falhas nem produzir novos logs. Além disso, os 11 testes de conformidade arquitetural e tipagem estática localizados no diretório raiz 	ests/ estavam sendo omitidos tanto nos testes de PR quanto nos lançamentos devido à sua ausência no sparse-checkout.

Essa falha decorre da confluência de três problemas fundamentais:
1. **Suspensão de processo pelo Windows Error Reporting**: Em runners headless do Windows no GitHub Actions, o utilitário WerFault.exe suspende workers do pytest-xdist que sofrem Access Violation (0xc0000005) em segundo plano, mantendo seus pipes IPC abertos e impedindo que o pytest detecte o término do worker para substituí-lo.
2. **Ciclo de vida e acúmulo de widgets Qt na heap**: Em ditor/legacy_views/area_principal.py, cada instanciação de JanelaPrincipal cria 4 widgets temporários que são imediatamente descartados com deleteLater(), acumulando eventos de desalocação tardia no loop de eventos do pytestqt sob o driver offscreen. Nos testes, dezenas de instâncias de JanelaPrincipal eram criadas sem fixture de encerramento com 	eardown ordenado (close()).
3. **Incompletude do sparse-checkout**: O diretório 	ests/ não estava mapeado no sparse-checkout dos workflows do GitHub Actions, gerando assimetria entre as validações locais (1.263 testes) e no CI (1.252 testes) e violando o princípio de 100% de cobertura e verificação estrita.

A resolução desses problemas segue rigorosamente os mandamentos de PRINCIPIOS.md: nomenclatura integral em português brasileiro, simplicidade declarativa contra abstrações prematuras, desenvolvimento orientado a testes (TDD) com ciclo Red-Green-Refactor e testes de integração em primeiro lugar.

## What Changes

- **Inclusão de 	ests/ no sparse-checkout de todos os fluxos de teste**: Adiciona o diretório 	ests à lista de checkout nos workflows .github/workflows/pr-code-validator.yml e .github/workflows/release-editor.yml, restaurando a execução dos testes de conformidade arquitetural e tipagem estrita (mypy --strict).
- **Desativação de diálogos e suspensão pelo WerFault no Windows**: Configura o registro do Windows no início dos jobs do Windows para desativar a interface e o bloqueio do Windows Error Reporting (DontShowUI=1, Disabled=1), garantindo término imediato em falhas não tratadas e detecção nativa pelo pytest-xdist.
- **Eliminação de alocações efêmeras e deleteLater() na PaginaBase**: Refatora a hierarquia de páginas da JanelaPrincipal para que páginas com layout próprio (PaginaDados, PaginaImagens, PaginaMapas, PaginaBetas) configurem seu layout diretamente, sem instanciar nem descartar QLabel com deleteLater().
- **Fixture de teste com teardown garantido (yield + janela.close())**: Introduz e adota fixture padronizada do pytest com fechamento ordenado da JanelaPrincipal em ditor/legacy_views/area_principal_test.py, assegurando que a desmontagem dos recursos ocorra antes do processamento final de eventos do pytestqt.
- **Deduplicação e higienização em rea_principal_test.py**: Remove o bloco de quase 200 linhas de testes duplicados (linhas 455 a 640), alinhando a suíte à regra de ouro da simplicidade e manutenibilidade.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade funcional de produto; as alterações aprimoram a infraestrutura de CI/CD, a estabilidade interna da janela principal e a robustez da suíte de testes).*

### Modified Capabilities
- ditor-cicd-pipeline: Exige inclusão de 	ests/ no sparse-checkout dos workflows de CI/CD e configuração de supressão de bloqueios do Windows Error Reporting no runner de Windows.
- ditor-area-principal: Requer que a instanciação das páginas da janela principal não aloque widgets redundantes marcados para destruição tardia, e que a suíte de testes utilize fixtures com ciclo de vida e fechamento ordenado (	eardown com close()).

## Impact

- **Workflows GitHub Actions**: Atualização de .github/workflows/release-editor.yml e .github/workflows/pr-code-validator.yml.
- **Módulos do Editor**: Refatoração limpa em ditor/legacy_views/area_principal.py e saneamento em ditor/legacy_views/area_principal_test.py.
- **Estatísticas de Teste**: Total de 1.263 testes executados de ponta a ponta no CI (eliminando a discrepância dos 11 testes ausentes de 	ests/).
- **Resiliência e Tempo**: Eliminação definitiva do travamento por timeout de 10 minutos no runner Windows durante os lançamentos.