# Spec Delta

## MODIFIED Requirements

### Requirement: Motor de Migração Sequencial
O sistema SHALL disponibilizar um motor de migração offline que identifica, ordena e executa scripts de migração de forma sequencial em cada croqui desatualizado. A execução deve ocorrer automaticamente em duas situações: no deploy/compilação e ao abrir um croqui no Editor. A localização dos scripts de migração e a consulta de versão máxima SHALL funcionar de maneira resiliente tanto em ambiente de desenvolvimento quanto em distribuições compiladas/empacotadas (PyInstaller).

#### Scenario: Execução de migrações pendentes
- **WHEN** um croqui com `ultima_migracao` antiga é processado
- **THEN** o motor SHALL executar sequencialmente todos os scripts da pasta `/migracoes/` cujos números de versão sejam superiores à `ultima_migracao` registrada no croqui
- **AND** o motor SHALL atualizar o valor de `ultima_migracao` em `croqui.yaml` para o número do último script executado com sucesso

#### Scenario: Ignorar migrações já aplicadas
- **WHEN** todos os scripts em `/migracoes/` têm números menores ou iguais à `ultima_migracao` registrada no croqui
- **THEN** o motor SHALL ignorar a execução desses scripts e prosseguir com o fluxo normal

#### Scenario: Resolução de scripts em ambiente empacotado
- **WHEN** o motor de migração ou a consulta de versão máxima for invocada dentro de um aplicativo empacotado
- **THEN** o sistema SHALL localizar os scripts embutidos no pacote ou realizar fallback seguro para o diretório de migrações do repositório base sincronizado localmente
- **AND** retornar a versão correta da última migração sem retornar 0 indevidamente
