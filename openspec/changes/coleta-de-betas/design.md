## Context

Com o croqui migrado para Protobuf (`compilado.binarypb`), queremos conectar as escaladas a vídeos reais no YouTube e posts no Instagram. Durante o `/opsx-explore`, decidimos que o pipeline de busca será orquestrado via Antigravity Workflows usando APIs oficiais, aliado a uma camada de extração de metadados por LLM. Estes resultados passarão por revisão humana num painel local (PyQt).

## Goals / Non-Goals

**Goals:**
- Implementar toda a lógica da funcionalidade de forma **auto-contida e modular** em uma pasta dedicada `coleta_de_betas/` (Library-First), com testes co-localizados (`*_test.py` ao lado de cada `*.py`).
- Implementar Worker de scraping usando uma rede ampla: APIs oficiais do Google (YouTube v3 + Vertex AI Search) e web scraping gratuito (`duckduckgo-search`).
- Isolar a definição dos schemas de betas em um arquivo `.proto` dedicado (`beta.proto`) contendo a mensagem raiz `BetasPendentes` para o artefato intermediário `betas_pendentes.binarypb`, e importar em `croqui.proto` para a consolidação final.
- Integrar LLMs via sub-agentes para avaliar relevância e extrair o beta (crux/movimentos) dos textos originais de todos os resultados da busca cruzada, separando o sinal do ruído.
- Apresentar os resultados capturados e seus scores em uma UI nativa (PyQt) para aprovação manual com visualização de thumbnails em formato de lista.
- Persistir as mídias aprovadas diretamente nos arquivos fonte Markdown/YAML (origem), para torná-las idempotentes frente ao processo de compilação geral do croqui.
- Adicionar verificação de saúde no `STATUS_CROQUIS.md` sinalizando croquis com pendências de curadoria de betas como um estado que exige atenção (⚠️/❌).

**Non-Goals:**
- Abolir a revisão humana. A curadoria sempre terá a chancela de um editor.
- Criar pastas separadas de teste; cada módulo terá seus testes co-localizados no mesmo diretório.

## Decisions

- **Estrutura Auto-Contida com Testes Co-localizados (`coleta_de_betas/`)**: Todo o código e seus respectivos testes (`*_test.py`) ficarão juntos nos submódulos de `coleta_de_betas/`:
  - `coleta_de_betas/extratores/`: `youtube.py`, `youtube_test.py`, `vertex.py`, `vertex_test.py`, `duckduckgo.py`, `duckduckgo_test.py`, `deduplicador.py`, `deduplicador_test.py`.
  - `coleta_de_betas/inteligencia/`: `avaliador.py`, `avaliador_test.py`.
  - `coleta_de_betas/curadoria/`: `painel_curadoria.py`, `painel_curadoria_test.py`, `carregador_imagens.py`, `carregador_imagens_test.py`.
  - `coleta_de_betas/persistencia/`: `salvamento.py`, `salvamento_test.py`.
- **Mecanismo de Busca Triplo**: **YouTube Data API v3**, **Vertex AI Search** e **duckduckgo-search**. *Rationale*: Nenhum motor de busca encontra 100% das postagens em redes fechadas como o Instagram. Lançar uma malha tripla aumenta o alcance (recall). O lixo retornado será filtrado pelo LLM. Bônus: O GCP permite 10.000 requisições/mês grátis no Agent Search, tornando a arquitetura gratuita. O cruzamento de fontes (ex: url do instagram que apareceu no Google e DDG com match no nome da via) gerará sinais fortes de relevância para facilitar a curadoria.
- **Protobuf Modular e Isolado (`beta.proto`)**: A ontologia de betas residirá em `aresta_api/proto/beta.proto`, incluindo `MidiaBeta`, `MetaBeta` e o container raiz `BetasPendentes` para serializar o arquivo `betas_pendentes.binarypb`. O `croqui.proto` importará `beta.proto` apenas para acoplar `repeated MidiaBeta betas = X;` na mensagem `Escalada`. *Rationale*: Separação de responsabilidades e desacoplamento do ciclo intermediário de processamento do compilado final do croqui.
- **Monitoramento de Saúde (`STATUS_CROQUIS.md`)**: O script `scripts/medir_saude_croquis.py` verificará a presença de arquivos `betas_pendentes.binarypb` ou registros de betas não curados. Se houver betas pendentes, a coluna indicará estado de atenção/não saudável.
- **Validação e Transparência LLM**: O orquestrador chamará sub-agentes Antigravity para analisar todos os snippets textuais trazidos pela busca. Todos os vídeos, independentemente de nota baixa, vão para a revisão UI (sem corte arbitrário da máquina), classificados por score. *Rationale*: Transparência. O LLM extrai valor informacional, e não apenas age como um filtro cego.
- **UI Qt (Curadoria)**: A renderização de thumbnails será via download nativo da imagem carregada num `QPixmap`. *Rationale*: Não poluir o editor com uma dependência pesadíssima como o Chromium (`QWebEngineView`). 
- **Engenharia e Arquitetura (PRINCIPIOS.md)**: Em estrita aderência ao documento de princípios, o módulo será construído sob uma abordagem **Library-First**, garantindo isolamento e 100% de unit test coverage. O ciclo de vida da implementação será forçadamente **TDD (Red-Green-Refactor)**, iniciando pelos testes de integração nas fronteiras das APIs. Qualquer abstração desnecessária será abolida.
- **Protobuf Design**: Os novos schemas (`MidiaBeta`, `MetaBeta`, `BetasPendentes`) seguirão o padrão rígido: enums encapsulados em suas próprias mensagens, inicializados obrigatoriamente com `INDEFINIDO = 0`, além de `oneof`s devidamente encapsulados.
- **Estratégia de Persistência**: A aplicação Python vai editar diretamente os arquivos `grupo_*.md`, adicionando a mídia no bloco YAML respectivo da via. *Rationale*: Mantém os arquivos como única fonte da verdade e permite regenerar o `compilado.binarypb` integralmente sem corrupção de dados a posteriori.

## Risks / Trade-offs

- **[Risco] Corrupção da Estrutura Markdown ao reescrever YAML** → *Mitigação*: Utilizar parser robusto (`ruamel.yaml` ou regex restrito ao escopo do frontmatter das vias) e garantir backup automático temporário ou reverter via controle de versão (Git) em caso de falha durante a persistência feita pelo editor Qt.
- **[Risco] Falsos Positivos da API de Busca consumindo o avaliador humano** → *Mitigação*: O LLM fornecerá o Score e a Justificativa (Reasoning). A interface do PyQt usará isso para rebaixar para o fundo da lista itens de baixa qualidade, deixando a UX fluida.
