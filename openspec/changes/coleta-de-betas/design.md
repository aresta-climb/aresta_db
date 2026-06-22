## Context

Com o croqui migrado para Protobuf (`compilado.binarypb`), queremos conectar as escaladas a vídeos reais no YouTube e posts no Instagram. Durante o `/opsx-explore`, decidimos que o pipeline de busca será orquestrado via Antigravity Workflows usando APIs oficiais, aliado a uma camada de extração de metadados por LLM. Estes resultados passarão por revisão humana num painel local (PyQt).

## Goals / Non-Goals

**Goals:**
- Implementar Worker de scraping usando uma rede ampla: APIs oficiais do Google (YouTube v3 + Vertex AI Search) e web scraping gratuito (`duckduckgo-search`).
- Integrar LLMs via sub-agentes para avaliar relevância e extrair o beta (crux/movimentos) dos textos originais de todos os resultados da busca cruzada, separando o sinal do ruído.
- Apresentar os resultados capturados e seus scores em uma UI nativa (PyQt) para aprovação manual com visualização de thumbnails em formato de lista.
- Persistir as mídias aprovadas diretamente nos arquivos fonte Markdown/YAML (origem), para torná-las idempotentes frente ao processo de compilação geral do croqui.

**Non-Goals:**
- Abolir a revisão humana. A curadoria sempre terá a chancela de um editor.

## Decisions

- **Mecanismo de Busca Triplo**: **YouTube Data API v3**, **Vertex AI Search** e **duckduckgo-search**. *Rationale*: Nenhum motor de busca encontra 100% das postagens em redes fechadas como o Instagram. Lançar uma malha tripla aumenta o alcance (recall). O lixo retornado será filtrado pelo LLM. Bônus: O GCP permite 10.000 requisições/mês grátis no Agent Search, tornando a arquitetura gratuita. O cruzamento de fontes (ex: url do instagram que apareceu no Google e DDG com match no nome da via) gerará sinais fortes de relevância para facilitar a curadoria.
- **Validação e Transparência LLM**: O orquestrador chamará sub-agentes Antigravity para analisar todos os snippets textuais trazidos pela busca. Todos os vídeos, independentemente de nota baixa, vão para a revisão UI (sem corte arbitrário da máquina), classificados por score. *Rationale*: Transparência. O LLM extrai valor informacional, e não apenas age como um filtro cego.
- **UI Qt (Curadoria)**: A renderização de thumbnails será via download nativo da imagem carregada num `QPixmap`. *Rationale*: Não poluir o editor com uma dependência pesadíssima como o Chromium (`QWebEngineView`). 
- **Engenharia e Arquitetura (PRINCIPIOS.md)**: Em estrita aderência ao documento de princípios, o worker **não** será um script acoplado; ele será construído sob uma abordagem **Library-First**, garantindo isolamento e 100% de unit test coverage. O ciclo de vida da implementação será forçadamente **TDD (Red-Green-Refactor)**, iniciando pelos testes de integração nas fronteiras das APIs. Qualquer abstração desnecessária será abolida.
- **Protobuf Design**: Os novos schemas (`MidiaBeta`, `MetaBeta`) seguirão o padrão rígido: enums encapsulados em suas próprias mensagens, inicializados obrigatoriamente com `INDEFINIDO = 0`, além de `oneof`s devidamente encapsulados.
- **Estratégia de Persistência**: A aplicação Python vai editar diretamente os arquivos `grupo_*.md`, adicionando a mídia no bloco YAML respectivo da via. *Rationale*: Mantém os arquivos como única fonte da verdade e permite regenerar o `compilado.binarypb` integralmente sem corrupção de dados a posteriori.

## Risks / Trade-offs

- **[Risco] Corrupção da Estrutura Markdown ao reescrever YAML** → *Mitigação*: Utilizar parser robusto (`ruamel.yaml` ou regex restrito ao escopo do frontmatter das vias) e garantir backup automático temporário ou reverter via controle de versão (Git) em caso de falha durante a persistência feita pelo editor Qt.
- **[Risco] Falsos Positivos da API de Busca consumindo o avaliador humano** → *Mitigação*: O LLM fornecerá o Score e a Justificativa (Reasoning). A interface do PyQt usará isso para rebaixar para o fundo da lista itens de baixa qualidade, deixando a UX fluida.
