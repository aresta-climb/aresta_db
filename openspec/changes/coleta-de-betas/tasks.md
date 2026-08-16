## 1. Schema Protobuf Modular (beta.proto) e Compilação (TDD First)

- [x] 1.1 Escrever testes unitários em `aresta_api/proto_validacao_test.py` ou `aresta_api/beta_proto_test.py` para as classes geradas do novo `beta.proto` (garantindo falha inicial - Red).
- [x] 1.2 Criar arquivo `aresta_api/proto/beta.proto` contendo as messages `MidiaBeta`, `MetaBeta` e a mensagem raiz `BetasPendentes`. Garantir estritamente: enums encapsulados com `INDEFINIDO = 0` e oneofs encapsulados, conforme `PRINCIPIOS.md`.
- [x] 1.3 Atualizar `aresta_api/build.py` para compilar o novo `beta.proto` gerando os stubs em Python e Dart e passando nos testes (Green).
- [x] 1.4 Importar `beta.proto` em `croqui.proto` e vincular o campo `repeated MidiaBeta betas = X;` na message `Escalada`.
- [x] 1.5 Modificar os scripts de compilação (parser YAML->Proto) para processar o bloco `betas` nos markdowns de vias (Green/Refactor com 100% coverage).

## 2. Módulo Auto-Contido e Worker de Extração (coleta_de_betas/extratores/)

- [x] 2.1 Criar a estrutura inicial do módulo `coleta_de_betas/` (`__init__.py`, `extratores/`, `inteligencia/`, `curadoria/`, `persistencia/`).
- [x] 2.2 TDD (Integração Primeiro): Escrever testes falhos em `coleta_de_betas/extratores/youtube_test.py` mockando os retornos da YouTube Data API v3.
- [x] 2.3 Implementar o extrator do YouTube em `coleta_de_betas/extratores/youtube.py` (Green/Refactor).
- [x] 2.4 TDD: Escrever testes falhos em `coleta_de_betas/extratores/vertex_test.py` e `coleta_de_betas/extratores/duckduckgo_test.py` para buscas no Instagram.
- [x] 2.5 Implementar os extratores `coleta_de_betas/extratores/vertex.py` e `coleta_de_betas/extratores/duckduckgo.py` (Green/Refactor) mantendo 100% de coverage.
- [x] 2.6 TDD: Escrever testes em `coleta_de_betas/extratores/deduplicador_test.py` e implementar `coleta_de_betas/extratores/deduplicador.py` com deduplicação cruzada de URLs.

## 3. Inteligência e Agente LLM (coleta_de_betas/inteligencia/)

- [x] 3.1 TDD: Escrever testes em `coleta_de_betas/inteligencia/avaliador_test.py` para as funções de prompt e parsing de JSON da LLM.
- [x] 3.2 Implementar o cliente de IA em `coleta_de_betas/inteligencia/avaliador.py` processando candidatos em batch (Green/Refactor).
- [x] 3.3 Processar outputs forçando JSON-schema para extrair `llm_confidence_score`, `llm_reasoning` e `resumo_do_movimento` sob 100% de coverage.
- [x] 3.4 Implementar rotina que serializa o staging `betas_pendentes.binarypb` usando a mensagem raiz `BetasPendentes`.

## 4. Aba de Curadoria PyQt (coleta_de_betas/curadoria/)

- [x] 4.1 TDD: Escrever testes em `coleta_de_betas/curadoria/painel_curadoria_test.py` e `coleta_de_betas/curadoria/carregador_imagens_test.py` para UI e downloads HTTP mockados.
- [x] 4.2 Criar os widgets e a aba de curadoria em `coleta_de_betas/curadoria/painel_curadoria.py` para carregar `betas_pendentes.binarypb` (Green/Refactor).
- [x] 4.3 Implementar worker assíncrono em `coleta_de_betas/curadoria/carregador_imagens.py` para download de thumbnails (`QPixmap`) com fallback para ícone do Instagram.
- [x] 4.4 Integrar a nova aba no `editor/` chamando os componentes desacoplados de `coleta_de_betas.curadoria`.

## 5. Edição In-Place, Saúde dos Croquis e Workflow

- [x] 5.1 TDD: Escrever testes unitários exaustivos em `coleta_de_betas/persistencia/salvamento_test.py` usando Markdowns simulados para garantir preservação do layout e injeção do YAML `betas`.
- [x] 5.2 Implementar rotina de persistência em `coleta_de_betas/persistencia/salvamento.py` (Green/Refactor).
- [x] 5.3 TDD: Atualizar `scripts/medir_saude_croquis.py` (e seu respectivo teste) para detectar croquis com `betas_pendentes.binarypb` e adicionar a coluna de status correspondente no `STATUS_CROQUIS.md`.
- [x] 5.4 Criar o arquivo de workflow final `.agents/workflows/coletar_betas.md` descrevendo como invocar o pipeline pelo Antigravity.
