## ADDED Requirements

### Requirement: Motor de Migração Sequencial
O sistema SHALL disponibilizar um motor de migração offline que identifica, ordena e executa scripts de migração de forma sequencial em cada croqui desatualizado. A execução deve ocorrer automaticamente em duas situações: no deploy/compilação e ao abrir um croqui no Editor.

#### Scenario: Execução de migrações pendentes
- **WHEN** um croqui com `ultima_migracao` antiga é processado
- **THEN** o motor SHALL executar sequencialmente todos os scripts da pasta `/migracoes/` cujos números de versão sejam superiores à `ultima_migracao` registrada no croqui
- **AND** o motor SHALL atualizar o valor de `ultima_migracao` em `croqui.yaml` para o número do último script executado com sucesso

#### Scenario: Ignorar migrações já aplicadas
- **WHEN** todos os scripts em `/migracoes/` têm números menores ou iguais à `ultima_migracao` registrada no croqui
- **THEN** o motor SHALL ignorar a execução desses scripts e prosseguir com o fluxo normal

### Requirement: Versionamento por Números Sequenciais
Toda migração SHALL ser identificada unicamente por um número sequencial de 4 dígitos prefixado no nome do seu arquivo script (ex: `0001_descricao.py`).

#### Scenario: Ordenação numérica de migrações
- **WHEN** o motor varre a pasta `/migracoes/`
- **THEN** ele SHALL ordenar os arquivos de migração numericamente para garantir a ordem exata de desenvolvimento

### Requirement: Testes Unitários de Migração
Todo script de migração `XXXX_descricao.py` (onde `XXXX` são os 4 dígitos sequenciais) SHALL ter um arquivo de teste correspondente nomeado `XXXX_descricao_test.py`.

#### Scenario: Validação automática de migração
- **WHEN** a suíte de testes é executada via Pytest
- **THEN** cada teste de migração SHALL usar os helpers de `scripts/helpers_migracao.py` para criar um croqui de teste temporário, aplicar a migração correspondente e validar a integridade dos dados migrados

#### Scenario: Garantir unicidade de IDs de migração
- **WHEN** a suíte de testes analisa todos os arquivos na pasta `/migracoes/`
- **THEN** o validador SHALL confirmar que nenhum ID (prefixo de 4 dígitos) está duplicado entre os arquivos de migração



### Requirement: Migração de Seções Textuais para Botões
O sistema SHALL migrar a estrutura legada de arquivos de seções textuais para o novo formato de botões interativos no schema do croqui.

#### Scenario: Conversão de secoes_textuais para botoes
- **WHEN** um croqui contendo a chave `secoes_textuais` (ou `arquivos_markdown`) é migrado pelo script de botões
- **THEN** o sistema SHALL mover o título para `Botao.texto` e o caminho do arquivo para `Botao.destino.secao_textual.caminho`
- **AND** remover as chaves `secoes_textuais` e `arquivos_markdown` antigas do `croqui.yaml`
