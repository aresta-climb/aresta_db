# Tasks

## 1. Localizador em Cascata e Extrator de Contexto do Feedback

- [x] 1.1 Criar os testes orientados a comportamento em `serving/agente_feedback/localizador_arquivos_croqui_test.py` cobrindo: extração de `croqui_id`, `Setor (...)`, `Via (...)` e URL de captura de tela a partir do corpo da Issue; localização determinística do `.md` pelo nome do setor/via; localização por busca textual local normalizada; e geração do índice compacto de `database/<croqui_id>/` (sem coordenadas de mapas), verificando que os testes falham inicialmente (Red)
- [x] 1.2 Implementar `serving/agente_feedback/localizador_arquivos_croqui.py` e verificar que todos os testes em `serving/agente_feedback/localizador_arquivos_croqui_test.py` passam com 100% de cobertura via `uv run pytest serving/agente_feedback/localizador_arquivos_croqui_test.py --cov=serving.agente_feedback.localizador_arquivos_croqui --cov-fail-under=100`

## 2. Renderizador de Régua Cartesiana em Imagens de Mapa

- [x] 2.1 Criar os testes em `serving/agente_feedback/renderizador_regua_mapa_test.py` validando que uma imagem de mapa com `largura_mapa`, `altura_mapa` e `pontos_de_interesse` é renderizada em memória com margens graduadas nos eixos X e Y, linhas de grade e rótulos dos pontos sem alterar o arquivo original em disco, verificando a falha inicial (Red)
- [x] 2.2 Implementar `serving/agente_feedback/renderizador_regua_mapa.py` usando `Pillow` e verificar aprovação integral e 100% de cobertura via `uv run pytest serving/agente_feedback/renderizador_regua_mapa_test.py --cov=serving.agente_feedback.renderizador_regua_mapa --cov-fail-under=100`

## 3. Clientes de Fronteira Externa (Gemini Flash e GitHub API) e Fakes Determinísticos

- [x] 3.1 Criar a biblioteca Fake `serving/agente_feedback/cliente_gemini_feedback_fake.py` e seu teste espelhado `serving/agente_feedback/cliente_gemini_feedback_fake_test.py` (simulando respostas de desambiguação de arquivos, propostas de alteração estruturadas, feedbacks não acionáveis, autoretry e falhas determinísticas de rede/cota), verificando 100% de cobertura com `uv run pytest serving/agente_feedback/cliente_gemini_feedback_fake_test.py`
- [x] 3.2 Criar `serving/agente_feedback/cliente_gemini_feedback_test.py` e implementar `serving/agente_feedback/cliente_gemini_feedback.py` usando servidor HTTP local real em memória nos testes para validar o envio multimodal (texto + screenshot + mapas com régua + schema JSON estrito) à API REST do Google AI Studio (`gemini-2.5-flash`), verificando 100% de cobertura com `uv run pytest serving/agente_feedback/cliente_gemini_feedback_test.py --cov=serving.agente_feedback.cliente_gemini_feedback --cov-fail-under=100`
- [x] 3.3 Criar a biblioteca Fake `serving/agente_feedback/cliente_github_feedback_fake.py` (+ `cliente_github_feedback_fake_test.py`) e a implementação `serving/agente_feedback/cliente_github_feedback.py` (+ `cliente_github_feedback_test.py`) para buscar dados de Issue/PR, comentários, baixar anexos de imagem, criar/atualizar Pull Requests e publicar comentários, verificando 100% de cobertura com `uv run pytest serving/agente_feedback/cliente_github_feedback*_test.py`

## 4. Orquestrador de Resolução Segura (Hard Jail, Validação Local e Autoretry) e CLI

- [x] 4.1 Escrever os testes de integração e comportamento em `serving/agente_feedback/orquestrador_resolucao_feedback_test.py` cobrindo: fluxo completo de Issue `feedback:croqui` acionável e não acionável; comando `/ai-fix` em Issue (criando nova PR ou atualizando PR existente) e direto em PR; bloqueio de alterações fora de `database/<croqui_id>/*.{md,yaml}` (Hard Jail e preservação SPDX); e autoretry quando a validação do croqui falha na primeira tentativa, verificando a falha inicial (Red)
- [x] 4.2 Implementar `serving/agente_feedback/orquestrador_resolucao_feedback.py` e o ponto de entrada CLI `serving/resolver_feedback_ia.py` (com seu respectivo `serving/resolver_feedback_ia_test.py`), verificando 100% de cobertura em todo o pacote via `uv run pytest serving/agente_feedback/ serving/resolver_feedback_ia_test.py --cov=serving.agente_feedback --cov=serving.resolver_feedback_ia --cov-fail-under=100`

## 5. Workflow GitHub Actions, Documentação do AI Studio e Verificação Final

- [x] 5.1 Criar o workflow `.github/workflows/ai-feedback-solver.yml` configurado para `issues: [opened, labeled]` (label `feedback:croqui`) e `issue_comment: [created]` (contendo `/ai-fix` de `OWNER`, `MEMBER` ou `COLLABORATOR`), utilizando `actions/create-github-app-token@v3` com downscoping (`permission-contents: write`, `permission-pull-requests: write`, `permission-issues: write`) e verificar a sintaxe YAML e regras do workflow
- [x] 5.2 Criar o guia detalhado `docs/guia_configuracao_ai_studio_feedback.md` (explicando como gerar a chave gratuita `GEMINI_API_KEY` no Google AI Studio sem cobrança, diferença em relação ao Google One AI Ultra, configuração de Secrets no GitHub e uso do comando `/ai-fix`) e atualizar o `README.md`, verificando que os caminhos e instruções estão completos
- [x] 5.3 Executar a verificação de qualidade estática (`uv run ruff check serving/` e `uv run mypy serving/agente_feedback serving/resolver_feedback_ia.py`) e a suíte de testes garantindo zero erros e 100% de cobertura nos novos módulos
