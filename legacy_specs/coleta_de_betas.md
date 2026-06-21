# Design Proposal: Pipeline Agentic de Coleta e Validação de Betas

## 1. Visão Geral

**Objetivo:** Enriquecer o banco de dados de croquis com links de vídeos
(betas/cadenas) extraídos do YouTube e do Instagram, criando um ecossistema onde
o escalador tem a informação visual a um clique de distância no aplicativo.

**Estratégia Central:** Utilizar um fluxo de trabalho orquestrado em um workflow
do Google Antigravity para acionar workers isolados em Python. A busca é feita
em fontes oficiais/seguras e a triagem é realizada por sub-agentes de IA para
garantir alta precisão.

**Fase Inicial:** 100% de curadoria manual em um painel administrativo antes da
injeção no banco de produção.

---

## 2. Arquitetura do Sistema

A arquitetura separa as responsabilidades de estado (workflow Antigravity),
extração (Python) e inteligência (LLM).

- **Orquestrador (Antigravity Workflows):** Gerencia a fila de vias, os retries,
  a execução dos scripts e o merge final dos dados.
- **Workers de Extração (Python Async):** Scripts sem estado responsáveis por
  fazer as requisições HTTP e lidar com paginação/rate limits.
  - _Fonte 1:_ YouTube Data API v3.
  - _Fonte 2:_ Google Custom Search API (Programmable Search Engine) atuando
    como proxy para indexação do Instagram.
- **Motor de Inteligência (Sub-agentes Antigravity):** Pipeline de sub-agentes.
  Processa os metadados brutos e retorna um veredito estruturado.
- **Armazenamento:** Sub-protos do protobuf de Croqui.

---

## 3. O Fluxo de Execução (Pipeline Agentic)

O pipeline roda em lotes (ex: 50 escaladas por execução) para não sobrecarregar
as APIs e os sub-agentes.

### Fase 1: Trigger e Preparação

1. O workflow do Antigravity levanta uma lista de escaladas ativas (ID, Nome,
   Setor, Pico).
2. O payload inicial é passado para o ambiente de execução do script Python.

### Fase 2: Scraping Paralelo (Tool Callers)

1. O script gera variações de query (ex:
   `"{Nome da escalada}" + "{Pico}" + escalada`).
2. Requisições assíncronas batem na API do YouTube e na API do Google Custom
   Search (restrita a `site:instagram.com/reel` OR `site:instagram.com/p`).
3. O script normaliza as respostas em uma lista consolidada de vídeos candidatos
   (Título, Snippet/Descrição, URL).

### Fase 3: Avaliação em Cascata (Sub-Agentes)

Os candidatos entram no funil do LLM. Se um agente reprovar, a execução daquele
vídeo é abortada, poupando tokens.

1. **Agente de Contexto:** Avalia se o texto/metadado do vídeo tem relação
   genuína com o esporte "escalada em rocha" (Filtro de falsos positivos
   homônimos).
2. **Agente Geográfico:** Cruza os dados do vídeo com a localização (Setor/Pico)
   e o nome da via do banco de dados.
3. **Juiz de Confiança:** Analisa se o vídeo tem intenção de ser um beta,
   atribuindo um `llm_confidence_score` (0 a 100) e gerando um `llm_reasoning`
   curto para auditoria. _Para o Instagram, o prompt instruirá a IA a considerar
   que o "snippet" é um texto truncado._

### Fase 4: Injeção e Curadoria

O script Python compila os resultados e devolve o output final para o node do
Antigravity. Nesta fase inicial de validação, **todos** os vídeos irão para uma
tabela temporária de `pending_betas` para aprovação humana através de um painel
de moderação escrito em html simples que vai permitir a quem executou o workflow
validar os resultados e aprovar ou rejeitar cada vídeo individualmente. Os
vídeos estarão ordenados em ordem decrescente de score da LLM e poderão ser
filtrados por fonte (youtube ou instagram. Padrão inicial mostrar os dois
juntos) e score mínimo no painel (padrão inicial 0, ou seja, mostrar todos).

---

## 4. Contrato de Dados (Payload de Integração)

Esta é uma proposta de JSON que o worker Python deve devolver para o Antigravity
no fim da execução. Idealmente na proposta formal devemos estruturar isso em um
Protobuf, para que o formato seja estaticamente tipado. Idealmente deve ser tudo
em português também.

```json
{
    "workflow_execution_id": "run_001_beta_crawler",
    "timestamp": "2026-06-21T10:00:00Z",
    "summary": {
        "routes_processed": 50,
        "total_candidates_found": 84,
        "videos_passed_llm": 12
    },
    "payload": [
        {
            "route_id": "uuid-da-via-no-banco",
            "route_name": "Nome da Via",
            "sector": "Nome do Setor",
            "verified_betas": [
                {
                    "source": "youtube",
                    "url": "[https://youtube.com/watch?v=](https://youtube.com/watch?v=)...",
                    "title": "Cadena Via X - Pico Y",
                    "thumbnail_url": "https://...",
                    "llm_confidence_score": 95,
                    "llm_reasoning": "O vídeo menciona explicitamente o nome da via e o pico. A descrição detalha os movimentos da escalada."
                },
                {
                    "source": "instagram_pse",
                    "url": "[https://instagram.com/p/](https://instagram.com/p/)...",
                    "title": "EscaladorBR on Instagram: Mandando a Via X...",
                    "thumbnail_url": null,
                    "llm_confidence_score": 75,
                    "llm_reasoning": "O snippet truncado confirma o nome da via, mas não detalha o setor. Contexto de escalada é forte."
                }
            ]
        }
    ]
}
```
