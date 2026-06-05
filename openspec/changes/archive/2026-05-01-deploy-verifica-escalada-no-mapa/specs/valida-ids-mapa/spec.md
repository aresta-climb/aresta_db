## ADDED Requirements

### Requirement: Validação de Referência de ID de Mapa
O sistema DEVE validar que todos os campos de identificação em mapas dentro de uma `Escalada` (`id_no_mapa`, `id_no_mapa_meio`, `id_no_mapa_fim`) correspondam a um `id` existente em pelo menos um `PontoDeInteresse` de um `Mapa` associado ao `Setor` ou `Grupo` onde a escalada está localizada.

#### Scenario: Escalada com IDs válidos
- **WHEN** uma escalada possui `id_no_mapa="1"` e existe um mapa no setor com um ponto de interesse de ID "1"
- **THEN** a validação deve passar sem erros

#### Scenario: Escalada com ID inexistente
- **WHEN** uma escalada possui `id_no_mapa="99"` mas nenhum mapa no setor ou grupo possui um ponto de interesse com ID "99"
- **THEN** a validação deve falhar e registrar um erro detalhando o arquivo, a via e o ID inválido

### Requirement: Coleta e Relato de Múltiplos Erros
O sistema DEVE acumular todos os erros de validação de IDs de mapa encontrados em um único croqui e exibi-los de forma agrupada quando a compilação desse croqui falhar.

#### Scenario: Croqui com múltiplos erros de ID
- **WHEN** um croqui possui três vias com IDs de mapa inexistentes
- **THEN** o sistema deve imprimir uma única mensagem de erro para o croqui contendo a lista das três vias e seus respectivos IDs inválidos

### Requirement: Resiliência do Pipeline de Deploy
O script de deploy DEVE continuar processando todos os croquis disponíveis, independentemente de falhas de validação em croquis individuais.

#### Scenario: Falha em um croqui no deploy global
- **WHEN** o deploy é executado para todos os croquis e o primeiro croqui falha na validação de IDs
- **THEN** o sistema deve reportar o erro do primeiro croqui e continuar a compilação do segundo croqui em diante

### Requirement: Resumo Final de Execução
Ao final da execução, o script de deploy DEVE exibir um resumo contendo o total de croquis processados com sucesso e o total de falhas.

#### Scenario: Fim do deploy com erros
- **WHEN** o deploy termina após encontrar erros em 2 de 10 croquis
- **THEN** o sistema deve exibir uma mensagem final indicando "Total compilados: 8 de 10" e "Total erros: 2"
