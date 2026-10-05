# Spec Delta: identificadores-estaveis

## Purpose

Garante a integridade referencial física e digital permanente através de UIDs descentralizados no banco fonte e tabelas locais de mapeamento para inteiros estáveis e compactos em três níveis hierárquicos: `croqui_id_numerico` (global), `entidade_id_numerico` (local para grupos, setores e escaladas) e `ponto_id_numerico` (local para pontos de interesse e nós de mapa), sem exigir sequencialidade contígua estrita nem contadores de sequência no catálogo, suportando migrações exclusivas de database e validação contratual estrita.

## ADDED Requirements

### Requirement: UIDs Descentralizados no Banco de Dados Fonte
O sistema SHALL atribuir a toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`) um `uid` permanente em formato NanoID Base62 com 12 caracteres agrupados por hífens (`xxxx-xxxx-xxxx`), garantindo colisão nula entre edições assíncronas em forks distintos.

#### Scenario: Criação de Nova Entidade no Editor
- **WHEN** o usuário cria uma nova Escalada, Setor, Grupo ou Ponto de Interesse no editor
- **THEN** o sistema gera automaticamente um `uid` válido no formato `^[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}$` e o associa à entidade

#### Scenario: Atribuição Automática a Entidades Existentes
- **WHEN** o compilador processa arquivos do `database/` contendo entidades sem `uid`
- **THEN** o sistema gera um `uid` determinístico ou único para cada uma e regrava o arquivo fonte

### Requirement: Tabelas de Mapeamento em Três Níveis (Snag)
O sistema SHALL manter tabelas de mapeamento biunívocas em arquivos YAML enxutos estruturadas em três níveis hierárquicos:
1. **Nível 1 (Global)**: `ids_globais.yaml` para `croqui_id_numerico`
2. **Nível 2 (Local - Entidades)**: `ids_entidades.yaml` para `entidade_id_numerico` (Grupos, Setores e Escaladas)
3. **Nível 3 (Local - Pontos)**: `ids_pontos.yaml` para `ponto_id_numerico` (Pontos de Interesse de Mapas)
contendo estritamente os campos `id` (inteiro positivo) e `uid` (string), sem duplicação de nomes ou slugs. Os IDs não precisam ser estritamente sequenciais contíguos (furos/gaps são válidos e tolerados) e o catálogo não mantém contadores centrais de sequência no Protobuf.

#### Scenario: Separação de Namespaces Locais
- **WHEN** o sistema aloca IDs numéricos para um croqui
- **THEN** ele registra Grupos, Setores e Escaladas em `ids_entidades.yaml` (`entidade_id_numerico`), e Pontos de Interesse visuais em `ids_pontos.yaml` (`ponto_id_numerico`), impedindo que POIs inflem a contagem das placas de inox

#### Scenario: Alocação Incremental de Inteiros Livres (Gaps Permitidos)
- **WHEN** uma entidade possui `uid` que ainda não consta na tabela de mapeamento correspondente
- **THEN** o sistema aloca o próximo inteiro livre disponível (ex: `max(ids) + 1` ou qualquer ID não utilizado) e anexa a entrada no final do arquivo YAML, sem exigir contiguidade ou renumeração de buracos

### Requirement: Resolução Semântica de Conflitos em Tabelas de IDs
O sistema SHALL fornecer capacidade autônoma de resolver conflitos de merge nos arquivos de mapeamento de IDs nos três níveis, operando puramente sobre arquivos de texto de forma 100% independente do binário do Git.

#### Scenario: Resolução de Conflitos com Split de Visões
- **WHEN** o sistema detecta marcadores de conflito do Git (`<<<<<<<` e `>>>>>>>`) em um arquivo de IDs
- **THEN** ele reconstitui as visões HEAD e Conflitante como documentos YAML válidos, preserva as entradas do HEAD com seus IDs oficiais e reatribui novos inteiros livres apenas para os UIDs novatos

### Requirement: Omissão de UIDs no Compilado para Disciplina de Bytes
O compilador SHALL omitir os campos `uid` na serialização final de `compilado.binarypb`, gerando o arquivo binário exclusivamente com os inteiros estáveis `croqui_id_numerico`, `id` (`entidade_id_numerico`), `alvo_id` (`entidade_id_numerico`) e `pontos_ids` (`ponto_id_numerico`).

#### Scenario: Minimização de Tamanho de Download
- **WHEN** o `deploy_generated` compila um croqui para consumo offline
- **THEN** o arquivo `compilado.binarypb` gerado não contém strings de UID, minimizando o consumo de armazenamento no dispositivo do usuário

### Requirement: Resolução O(1) Reativa de Entidades por ID
O sistema SHALL disponibilizar uma tabela indexada em memória que permita resolver em tempo O(1) qualquer entidade e seus ancestrais pelo seu ID numérico compacto (`entidade_id_numerico`), atualizada reativamente a cada mutação do croqui.

#### Scenario: Consulta Direta por ID de Escalada
- **WHEN** o sistema recebe uma consulta por um ID de escalada válido
- **THEN** ele retorna instantaneamente o objeto da escalada, seu setor pai e seu grupo pai sem varredura linear

### Requirement: Suporte a Migrações Database-Only sem Impacto no Serving
O sistema SHALL suportar scripts de migração com escopo restrito aos dados fonte e croquis experimentais (`AFETA_VERSAO_SERVING = False`), impedindo que o módulo de atualização do serving (`update_serving.py`) incremente a versão dos dados (`kDataVersion`), mantendo o serving de produção inalterado em `v4`.

#### Scenario: Execução de Migração Database-Only
- **WHEN** uma migração com `AFETA_VERSAO_SERVING = False` está presente na pasta `migracoes/`
- **THEN** a função `get_db_version()` ignora essa migração no cálculo da versão do serving, mantendo a versão correspondente à última migração estrutural pública

### Requirement: Testes de Contrato para Banco de Dados Fonte e Editor
O sistema SHALL fornecer uma suíte de testes de contrato automatizados que garantem a ausência de campos legados na pasta `database/` e atestam que as rotinas de serialização do editor não regridem gravando campos depreciados.

#### Scenario: Auditoria Contratual da Pasta Database
- **WHEN** os testes de contrato inspecionam os arquivos em `database/`
- **THEN** o teste falha se qualquer arquivo `.md` ou `croqui.yaml` contiver campos `id:` diretos (fora de arquivos de mapeamento `ids_*.yaml`), referências com `escalada:`, `setor:` ou `grupo:`, ou atributos `label:` em pontos de interesse

#### Scenario: Auditoria Contratual da Serialização do Editor
- **WHEN** o editor salva ou serializa dados modificados
- **THEN** a saída gerada não contém `id` direto nas entidades, não contém strings de caminho em referências de mapa, e utiliza exclusivamente `rotulo` para pontos de interesse

### Requirement: Migração Automática e Idempotente de Croquis Experimentais
O sistema SHALL fornecer o script de migração `migracoes/0005_migrar_uids_e_rotulos.py` para converter croquis experimentais e o acervo existente de forma transparente e idempotente para a arquitetura de UIDs, gerando arquivos de mapeamento nos três níveis e preservando comentários originais com `ruamel.yaml`.

#### Scenario: Carregamento de Croqui Experimental Antigo
- **WHEN** um croqui experimental com versão de migração anterior a 5 é aberto no editor ou processado por `migrar_banco.py`
- **THEN** o motor de migrações aplica a migração 5, gerando UIDs, mapeamentos em `ids_entidades.yaml` (`entidade_id_numerico`) e `ids_pontos.yaml` (`ponto_id_numerico`), convertendo referências para `alvo_uid`/`pontos_uids` e renomeando `label` para `rotulo`
