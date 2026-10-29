# Tasks

## 1. Esquema de Códigos `pr*` Unbounded (`>= 8` caracteres) no Editor Desktop

- [x] 1.1 Atualizar `editor/core/codigo_sessao_test.py` (ciclo Red) com testes comportamentais para validação e formatação de códigos Base36 `>= 8` caracteres (`unbounded`), geração/extração de código de Pull Request (`gerar_codigo_pull_request`, `extrair_numero_pull_request`, `eh_codigo_pull_request`) e verificação de reserva do prefixo `pr` para sessões normais do editor, confirmando a falha inicial com `uv run pytest editor/core/codigo_sessao_test.py`
- [x] 1.2 Implementar o suporte a códigos `>= 8` caracteres e as funções de código de Pull Request em `editor/core/codigo_sessao.py` (ciclo Green/Refactor), verificando 100% de cobertura comportamental com `uv run pytest editor/core/codigo_sessao_test.py --cov=editor.core.codigo_sessao --cov-report=term-missing`

## 2. Biblioteca de Diff Semântico e Visual de Croquis por UID (`serving/diff_croqui_pr_lib.py`)

- [x] 2.1 Criar `serving/diff_croqui_pr_lib_test.py` (ciclo Red) cobrindo cenários de croqui novo, croqui atualizado com pareamento por `uid` (picos, grupos, setores, escaladas renomeadas/editadas, mapas e pontos de interesse movidos/adicionados/removidos), diff de imagens de mapa/capa/thumbnail/Markdown e cópia seletiva de imagens modificadas ou removidas para `_base/<id>/`
- [x] 2.2 Implementar `serving/diff_croqui_pr_lib.py` (ciclo Green/Refactor) em português brasileiro sem mocks internos, verificando 100% de cobertura com `uv run pytest serving/diff_croqui_pr_lib_test.py --cov=serving.diff_croqui_pr_lib --cov-report=term-missing`

## 3. Biblioteca de Renderização do `resumo.html` e Comentário da PR (`serving/renderizador_resumo_pr_lib.py`)

- [x] 3.1 Criar `serving/renderizador_resumo_pr_lib_test.py` (ciclo Red) validando a geração do `resumo.html` autocontido (contadores e filtros, camada `<svg>` vetorial sobre mapas com modos `Diff/Antes/Depois/Ocultar`, modos `Lado a Lado` e `Slider Cortina` quando a imagem do mapa muda, galeria comparativa de imagens de capa/thumbnail/Markdown apontando para `_base`, QR Code SVG e links do app) e do Markdown enxuto do comentário contendo a assinatura `<!-- aresta-pr-validator -->`
- [x] 3.2 Implementar `serving/renderizador_resumo_pr_lib.py` (ciclo Green/Refactor), verificando 100% de cobertura comportamental com `uv run pytest serving/renderizador_resumo_pr_lib_test.py --cov=serving.renderizador_resumo_pr_lib --cov-report=term-missing`

## 4. Biblioteca de Publicação e Limpeza de PR no R2 com Fake Determinístico (`serving/publicador_pr_r2_lib.py`)

- [x] 4.1 Criar a biblioteca de Fake determinístico `serving/cliente_r2_fake.py` e sua suíte espelhada `serving/cliente_r2_fake_test.py` simulando operações de listagem, upload, leitura e exclusão em lote em memória (incluindo simulação determinística de falhas de I/O), verificando 100% de cobertura com `uv run pytest serving/cliente_r2_fake_test.py --cov=serving.cliente_r2_fake --cov-report=term-missing`
- [x] 4.2 Criar `serving/publicador_pr_r2_lib_test.py` e implementar `serving/publicador_pr_r2_lib.py` para publicar a pasta compilada da PR (incluindo `_base/` e `resumo.html`) sob `pr/<numero_pr>/`, remover objetos órfãos de execuções anteriores e excluir integralmente o prefixo `pr/<numero_pr>/` no fechamento da PR, verificando 100% de cobertura com `uv run pytest serving/publicador_pr_r2_lib_test.py --cov=serving.publicador_pr_r2_lib --cov-report=term-missing`

## 5. Integração no `serving/pr_db_validator.py` e Workflow `.github/workflows/pr-db-validator.yml`

- [x] 5.1 Refatorar `serving/pr_db_validator_test.py` (removendo antipadrões legados de `unittest.mock.patch` em código interno conforme Princípio VII do `AGENTS.md`) e adicionar testes para a geração do diff contra o diretório base, geração do `resumo.html`, publicação via `publicador_pr_r2_lib` e modo de limpeza (`--limpar-pr`), implementando as alterações em `serving/pr_db_validator.py` com 100% de cobertura verificada por `uv run pytest serving/pr_db_validator_test.py --cov=serving.pr_db_validator --cov-report=term-missing`
- [x] 5.2 Atualizar `.github/workflows/pr-db-validator.yml` para: (a) extrair o estado base de `origin/${{ github.base_ref }}` das pastas modificadas, (b) executar `serving/pr_db_validator.py` com publicação no R2 e geração do comentário, (c) deletar comentários anteriores do bot com `<!-- aresta-pr-validator -->` antes de postar o novo comentário no final da PR, e (d) adicionar o job de limpeza acionado em `pull_request: types: [closed]`

## 6. Roteamento Stateless de `pr*` e `/resumo/pr*` no Cloudflare Worker (`aresta_backend/cloudflare/previa`)

- [x] 6.1 Adicionar testes em `aresta_backend/cloudflare/previa/test/worker.test.ts` (ciclo Red) para códigos `>= 8` caracteres, bloqueio de prefixo `pr` em `gerarCodigoUnico()`, rejeição de `/ws` para códigos `pr*`, proxy *stateless* (sem `SessaoDurableObject`) de `/<codigo_pr>/*` para `https://serving.arestaclimb.com/pr/<numero_pr>/*`, rota `GET /resumo/<codigo_pr>` servindo `resumo.html` e exclusão de `/resumo/*` em `/.well-known/apple-app-site-association`
- [x] 6.2 Implementar as alterações em `aresta_backend/cloudflare/previa/src/gerenciador_sessao.ts` e `aresta_backend/cloudflare/previa/src/index.ts` (ciclo Green/Refactor), verificando que todos os testes passam em `aresta_backend/cloudflare/previa`

## 7. Suporte a Deep Link de Prévia e Códigos `pr*` no Aplicativo Móvel (`aresta_app/frontend`)

- [x] 7.1 Atualizar os testes unitários em `aresta_app/frontend/test/` (para `EditorDeCroqui` e navegação de Deep Links) cobrindo códigos `>= 8` caracteres, identificação de sessões `pr*` sem abertura de WebSocket `/events`, interceptação de `https://previa.arestaclimb.com/<codigo>` e `aresta://previa/<codigo>` para ativar a conexão experimental e desvio de `/resumo/*` para navegador externo
- [x] 7.2 Implementar o suporte em `aresta_app/frontend/lib/services/editor_croqui.dart`, `aresta_app/frontend/lib/navigation/servico_navegacao_deep_link.dart` e `aresta_app/frontend/android/app/src/main/AndroidManifest.xml`, verificando a aprovação integral da suíte `flutter test` correspondente
