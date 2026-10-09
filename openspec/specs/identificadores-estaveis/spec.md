# identificadores-estaveis Specification

## Purpose
Garante a integridade referencial física e digital permanente através do modelo **Pure NanoID 14c Universal** atribuído diretamente a todas as entidades no banco fonte (`database/`) e serializado no Protobuf (`compilado.binarypb`), eliminando a necessidade de tabelas intermediárias de mapeamento em YAML e descartando conflitos de merge de IDs no Git, viabilizando placas físicas permanentes em aço inox via `https://aresta.cc/<uid>` com QR Code de alta resiliência (Versão 3, Nível H), suportando migrações exclusivas de database e validação contratual estrita.

## Requirements

### Requirement: UIDs Descentralizados Universais no Banco de Dados Fonte e Compilado
O sistema SHALL atribuir a toda entidade (`Croqui`, `Grupo`, `Setor`, `Escalada` e `PontoDeInteresse`) um `uid` permanente em formato NanoID Base62 contínuo com 14 caracteres (`^[0-9a-zA-Z]{14}$`), garantindo espaço amostral de $1{,}24 \times 10^{25}$ combinações e probabilidade estatística de colisão nula, persistindo o UID tanto nos arquivos-fonte quanto no binário compilado (`compilado.binarypb`).

#### Scenario: Criação de Nova Entidade no Editor
- **WHEN** o usuário cria uma nova Escalada, Setor, Grupo ou Ponto de Interesse no editor
- **THEN** o sistema gera automaticamente um `uid` válido no formato `^[0-9a-zA-Z]{14}$` e o associa à entidade

#### Scenario: Atribuição Automática a Entidades Existentes
- **WHEN** o motor de migrações ou compilador processa arquivos do `database/` contendo entidades sem `uid`
- **THEN** o sistema gera um `uid` único de 14 caracteres para cada uma e regrava o arquivo fonte

#### Scenario: Serialização no Binário Compilado
- **WHEN** o `deploy_generated` compila um croqui para consumo offline
- **THEN** o arquivo `compilado.binarypb` gerado armazena diretamente o `uid` de 14 caracteres em cada entidade, sem descartá-lo e sem depender de tabelas intermediárias de tradução

### Requirement: Eliminação de Tabelas Intermediárias de Mapeamento
O sistema SHALL operar sem tabelas ou arquivos intermediários de mapeamento em YAML (`ids_globais.yaml`, `ids_entidades.yaml`, `ids_pontos.yaml`), eliminando a sobrecarga de gerenciar arquivos extras no repositório e descartando qualquer risco de conflito de merge de IDs no Git.

#### Scenario: Edições Concorrentes sem Conflito de Merge
- **WHEN** múltiplos colaboradores adicionam novas vias ou setores concorrentemente em forks ou branches distintos
- **THEN** o Git realiza o merge automático dos arquivos de conteúdo sem gerar conflitos de alocação de IDs, graças à unicidade estocástica universal do NanoID 14c

### Requirement: Placas Físicas e Links Canônicos Encurtados com aresta.cc
O sistema SHALL padronizar a identificação física permanente e o roteamento digital através do domínio encurtador `https://aresta.cc/<uid>` (totalizando exatamente 32 caracteres), dimensionado para gravação a laser em placas de aço inoxidável com QR Code Versão 3 (29x29) e Nível H de correção de erro (30% de tolerância a danos).

#### Scenario: Geração de Link Canônico Encurtado
- **WHEN** o sistema gera uma URL de compartilhamento ou prepara dados para gravação de placa física de uma entidade
- **THEN** a URL produzida segue estritamente o formato `https://aresta.cc/<uid>`, consumindo 32 caracteres

#### Scenario: Resiliência de Leitura Física em Ambiente Hostil
- **WHEN** um QR Code de placa de aço inox sofre arranhões mecânicos de mosquetão, acúmulo de pó de magnésio ou sujeira cobrindo até 30% da sua superfície
- **THEN** a leitura do QR Code Versão 3 com correção Nível H é realizada com sucesso devido à margem de recuperação de dados

### Requirement: Biblioteca Pura de Gerenciamento de UIDs
O sistema SHALL fornecer a biblioteca pura `gerenciar_uids_lib` para geração, validação e formatação de UIDs NanoID 14c Base62 e URLs `aresta.cc/<uid>`, com 100% de cobertura de testes unitários, encapsulando integralmente a biblioteca oficial de terceiros `nanoid`.

#### Scenario: Validação de UIDs no Pipeline
- **WHEN** o sistema valida um UID de entidade ou referência
- **THEN** a biblioteca rejeita cadeias que não contenham exatamente 14 caracteres alfanuméricos Base62 ou que contenham hífens, espaços ou caracteres especiais

#### Scenario: Encapsulamento Exclusivo da Biblioteca nanoid
- **WHEN** o sistema gera um UID
- **THEN** a chamada é realizada através de `gerenciar_uids_lib.gerar_uid()`, utilizando o algoritmo oficial do `nanoid` com o alfabeto Base62 e tamanho 14

### Requirement: Suporte a Migrações Database-Only sem Impacto no Serving
O sistema SHALL suportar scripts de migração com escopo restrito aos dados fonte e croquis experimentais (`AFETA_VERSAO_SERVING = False`), impedindo que o módulo de atualização do serving (`update_serving.py`) incremente a versão dos dados (`kDataVersion`), mantendo o serving de produção inalterado em `v4`.

#### Scenario: Execução de Migração Database-Only
- **WHEN** uma migração com `AFETA_VERSAO_SERVING = False` está presente na pasta `migracoes/`
- **THEN** a função `get_db_version()` ignora essa migração no cálculo da versão do serving, mantendo a versão correspondente à última migração estrutural pública

### Requirement: Testes de Contrato para Banco de Dados Fonte e Editor
O sistema SHALL fornecer uma suíte de testes de contrato automatizados que garantem a ausência de campos legados na pasta `database/`, atestam que as rotinas de serialização do editor não regridem gravando campos depreciados e asseguram que a biblioteca externa `nanoid` nunca seja importada diretamente fora de `scripts/gerenciar_uids_lib.py`.

#### Scenario: Auditoria Contratual da Pasta Database
- **WHEN** os testes de contrato inspecionam os arquivos em `database/`
- **THEN** o teste falha se qualquer arquivo contiver referências com `escalada:`, `setor:` ou `grupo:`, se pontos de interesse contiverem `label:`, se qualquer entidade não possuir `uid:` de 14 caracteres, ou se existirem arquivos residuais `ids_*.yaml`

#### Scenario: Auditoria Contratual da Serialização do Editor
- **WHEN** o editor salva ou serializa dados modificados
- **THEN** a saída gerada não contém strings de caminho em referências de mapa, utiliza exclusivamente `rotulo` para pontos de interesse e gera UIDs de 14 caracteres válidos

#### Scenario: Auditoria Contratual de Importação Exclusiva do nanoid
- **WHEN** a suíte de testes de contrato analisa a árvore de sintaxe abstrata (AST) de todos os arquivos Python do repositório
- **THEN** o teste falha se qualquer arquivo fora de `scripts/gerenciar_uids_lib.py` contiver declarações `import nanoid` ou `from nanoid import ...`

### Requirement: Migração Automática e Idempotente de Croquis Experimentais
O sistema SHALL fornecer o script de migração `migracoes/0005_migrar_uids_e_rotulos.py` para converter croquis experimentais e o acervo existente de forma transparente e idempotente para a arquitetura Pure NanoID 14c, sem criar arquivos de mapeamento YAML e preservando comentários originais com `ruamel.yaml`.

#### Scenario: Carregamento de Croqui Experimental Antigo
- **WHEN** um croqui experimental com versão de migração anterior a 5 é aberto no editor ou processado por `migrar_banco.py`
- **THEN** o motor de migrações aplica a migração 5, gerando UIDs de 14 caracteres, convertendo referências para `alvo_uid`/`pontos_uids`, renomeando `label` para `rotulo` e mantendo a integridade visual dos arquivos
