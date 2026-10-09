# agentes-extracao-pdf Specification

## Purpose

Define os comportamentos, contratos e diretrizes operacionais dos agentes autônomos e subagentes responsáveis pela extração de informações de croquis em PDF, conversão para Markdown e extração de mapas e pontos de interesse.

## Requirements

### Requirement: Geração de Frontmatter exclusivo para Mapas Gerais
O agente extrator (`ConversorMarkdown`) MUST criar o arquivo `mapas_gerais.md` apenas com conteúdo YAML Frontmatter, preenchendo a chave `mapas` de acordo com a extração de imagens. O corpo do markdown DEVE ser vazio.

#### Scenario: Processando um PDF de mapa geral
- **WHEN** o arquivo recebido for do tipo `mapas_gerais`
- **THEN** o agente gerará o `mapas_gerais.md` com `mapas: [caminho_imagem_mapa: ...]` e nenhum texto associado

### Requirement: Preservação Obrigatória de UIDs em Atualizações
Os agentes autônomos e skills de conversão e atualização (`converter_parte_croqui_para_markdown`, `processar_croqui_completo`, `atualizar_croqui_completo`) SHALL preservar integralmente todos os identificadores estáveis (`uid`, `alvo_uid`, `pontos_uids`) presentes em arquivos existentes durante rotinas de edição ou sincronização.

#### Scenario: Atualização de Setor Existente
- **WHEN** o subagente `ConversorMarkdown` edita um arquivo Markdown de setor que já contém UIDs de escaladas e referências de mapas
- **THEN** o subagente mantém todos os valores de `uid`, `alvo_uid` e `pontos_uids` inalterados no arquivo resultante

### Requirement: Padronização de Rótulos em Extração de Pontos de Interesse
As skills de extração e correção de mapas (`mapa_extrair_pontos_de_interesse`, `mapa_corrigir_pontos_de_interesse`) SHALL estruturar os metadados dos pontos de interesse utilizando exclusivamente o campo `rotulo` para o texto identificador visível, eliminando a dependência da chave legada `label`.

#### Scenario: Extração de Ponto de Interesse
- **WHEN** o agente executa a extração de pontos de interesse de uma imagem de mapa
- **THEN** o arquivo JSON gerado registra o texto do ponto na chave `rotulo` e preserva o campo `uid` caso este já exista

### Requirement: Suporte a Rascunho Semântico de Referências de Mapa
As skills e workflows de geração de novos croquis SHALL permitir que agentes e humanos rascunhem referências de mapa utilizando nomes legíveis de escaladas ou setores (`escalada: 'Nome'`, `ids: ['01']`), delegando a conversão determinística para `alvo_uid` e `pontos_uids` ao pipeline de compilação.

#### Scenario: Rascunho Inicial de Mapa em Novo Setor
- **WHEN** o subagente cria um novo arquivo de setor associando referências por nome textual da via
- **THEN** o compilador resolve os nomes contra os UIDs das escaladas criadas e substitui a referência semântica pelos campos canônicos `alvo_uid` e `pontos_uids`
