# Design

## Context

Conforme estabelecido em `proposal.md` (seção *Why*), as informações de inspeção, manutenção e estoque da Gruta da Lapinha (2026) precisam ser consolidadas em duas frentes complementares:
1. O aplicativo Aresta (`../aresta_app/frontend/lib/view/function_library/via_functions.dart`) já renderiza nativamente o campo `data_manutencao` de `ViaEsportiva`, `ViaMovel`, `ViaMultiplasEnfiadas` e `Highline` na seção **HISTÓRICO & CONQUISTA** da página da escalada.
2. O Relatório Consolidado no Google Docs (`1MDqztuc2f4zKHfUeX_xBjNso7Izohre6s53erApKYZY`) concentra os detalhes técnicos de ferragens, corrosão/palhetas e prestação de contas das doações ACEC-MG e Renato Utsch (`Relatorio doaçoes ACEC.pdf`, `09/11/2026`).

## Goals / Non-Goals

**Goals:**
- Atualizar os dados do croqui `br_mg_lagoa_santa_gruta_da_lapinha` via servidor MCP do Editor Aresta (`aresta_alterar_em_lote` / `aresta_alterar_campo`), compilando e salvando sem erros de validação.
- Atualizar o Google Docs `1MDqztuc2f4zKHfUeX_xBjNso7Izohre6s53erApKYZY` via CLI `gdocs` preservando a formatação de tabelas, cabeçalhos e links de pastas do Google Drive.

**Non-Goals:**
- Não alterar código-fonte do `aresta_app` (pois o campo `data_manutencao` já é exibido na página da escalada).
- Não incluir especificações técnicas de parafusos, chumbadores, resinas ou controle de estoque nas descrições das vias dentro do croqui do Aresta.

## Decisions

### 1. Separação entre Dados do Escalador (Aresta) e Relatório Técnico (Google Docs)
- **Decisão**: No croqui do Aresta, utilizar exclusivamente o campo `data_manutencao` para indicar quando a via passou por manutenção e manter o campo `descricao` restrito a alertas práticos de segurança ("beta de segurança") e interdições reais. Todo o detalhamento de ferragens instaladas, diagnóstico de corrosão/palhetas e prestação de contas de estoque permanece no Google Docs, referenciado por link em `creditos.md`.
- **Racional**: Evita poluir a tela do aplicativo com jargões de engenharia/estoque que não auxiliam a escalada em campo e previne duplicação de datas entre `data_manutencao` e `descricao`.

### 2. Atualização Atômica no Editor Aresta via MCP
- **Decisão**: Aplicar as mutações nas vias e nos créditos do croqui utilizando `aresta_alterar_em_lote` (ou `aresta_alterar_campo` para `creditos.md`) sobre o croqui aberto no Editor Aresta, seguido de `aresta_compilar` e `aresta_salvar`.
- **Racional**: Garante conformidade com o Princípio X do `AGENTS.md` (edições via comandos do histórico `QUndoStack`) e atualiza automaticamente os artefatos compilados em `generated/br_mg_lagoa_santa_gruta_da_lapinha/`.

### 3. Edição Cirúrgica do Google Docs via `gdocs`
- **Decisão**: Utilizar os subcomandos `gdocs mutate sed` e `gdocs mutate batch` / `update-table` no documento `1MDqztuc2f4zKHfUeX_xBjNso7Izohre6s53erApKYZY` (após verificar comentários existentes) para atualizar o Painel Geral (Parte I), as fichas das vias `76`, `78`, `79`, `82`, `86`, `87`, `88`, `92` e `99` (Parte III) e adicionar a seção de Controle de Estoque e Doações ACEC-MG + Renato Utsch (`09/11/2026`).
- **Racional**: Preserva a estrutura existente do documento e os links de fotos do Google Drive de todas as 53 vias.

## Risks / Trade-offs

- **[Risco] Desalinhamento entre contagens do PDF de estoque e fichas do Google Docs (ex.: via `94. Tripla Traição` cita 2 chapeletas PinGo no relato de campo de `05/09/2026` e 1 kit PinGo na tabela de estoque ACEC)** → **Mitigação**: Registrar a nota de conferência no Google Docs mantendo a tabela fiel ao `Relatorio doaçoes ACEC.pdf` (`09/11/2026`) e preservando o histórico de campo de `05/09/2026`.
