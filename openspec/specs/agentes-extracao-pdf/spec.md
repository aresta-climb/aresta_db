# agentes-extracao-pdf Specification

## Purpose

Define os comportamentos, contratos e diretrizes operacionais dos agentes autônomos e subagentes responsáveis pela extração de informações de croquis em PDF, conversão para Markdown e extração de mapas e pontos de interesse.

## Requirements

### Requirement: Geração de Frontmatter exclusivo para Mapas Gerais
O agente extrator (`ConversorMarkdown`) MUST preencher a entidade `ColecaoDeMapas` correspondente a `mapas_gerais` exclusivamente via ferramenta MCP `aresta_alterar_campo` no `UID` pré-alocado, populando a lista `mapas` sem escrever arquivos `.md` manualmente no disco.

#### Scenario: Processando um PDF de mapa geral
- **WHEN** a parte recebida pelo subagente for `mapas_gerais`
- **THEN** o subagente chama `aresta_alterar_campo` no `UID` da `ColecaoDeMapas` preenchendo `mapas: [{"caminho_imagem_mapa": ...}]` em uma única chamada atômica via MCP

### Requirement: Preservação Obrigatória de UIDs em Atualizações
Os agentes autônomos e skills de conversão e atualização (`converter_parte_croqui_para_markdown`, `processar_croqui_completo`, `atualizar_croqui_completo`) SHALL operar exclusivamente via ferramentas MCP do Editor Aresta (`aresta_alterar_campo`, `aresta_particionar_pdf_croqui`, `aresta_renderizar_mapa`, `aresta_compilar`, `aresta_salvar`), preservando integralmente todos os identificadores estáveis (`uid`, `alvo_uid`, `pontos_uids`) presentes nas entidades existentes e enviando a atualização de cada setor/grupo/mapa em uma única chamada MCP atômica escopada ao seu `UID`.

#### Scenario: Atualização de Setor Existente
- **WHEN** o subagente `ConversorMarkdown` atualiza um setor que já contém UIDs de escaladas e referências de mapas
- **THEN** o subagente inspeciona o setor com `aresta_obter_arvore(alvo=uid_setor)` e envia a atualização completa via `aresta_alterar_campo(alvo=uid_setor, campos={...})` mantendo todos os valores de `uid`, `alvo_uid` e `pontos_uids` inalterados, sem editar arquivos `.md` diretamente

### Requirement: Padronização de Rótulos em Extração de Pontos de Interesse
As skills de extração e correção de mapas (`mapa_extrair_pontos_de_interesse`, `mapa_corrigir_pontos_de_interesse`) SHALL inspecionar o mapa e seus recortes via `aresta_renderizar_mapa` e atualizar a lista `pontos_de_interesse` diretamente no `Mapa` via `aresta_alterar_campo` utilizando exclusivamente o campo `rotulo` para o texto identificador visível, sem usar arquivos intermediários em `raw_mapas/`.

#### Scenario: Extração de Ponto de Interesse
- **WHEN** o agente executa a extração ou correção de pontos de interesse de um mapa
- **THEN** o agente utiliza `aresta_renderizar_mapa` (com grade métrica e recortes ampliados por POI) e grava os pontos via `aresta_alterar_campo` na lista `pontos_de_interesse` do mapa com a chave `rotulo`, preservando o campo `uid` de pontos existentes

### Requirement: Suporte a Rascunho Semântico de Referências de Mapa
As skills e ferramentas MCP de geração e edição de croquis SHALL permitir vincular referências de mapa aos `UID`s das escaladas e pontos de interesse diretamente via `aresta_vincular_referencia_mapa` ou dentro do payload de `referencias` em `aresta_alterar_campo`.

#### Scenario: Rascunho Inicial de Mapa em Novo Setor
- **WHEN** o subagente cria ou atualiza um mapa de setor associando escaladas aos pontos de interesse extraídos
- **THEN** o subagente registra as referências canônicas (`alvo_uid` e `pontos_uids`) via MCP e valida a integridade com `aresta_compilar`
