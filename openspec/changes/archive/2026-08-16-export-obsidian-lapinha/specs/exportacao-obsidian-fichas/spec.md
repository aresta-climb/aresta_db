## ADDED Requirements

### Requirement: O sistema deve exportar dados das vias em template Markdown compatível com Obsidian
O sistema SHALL gerar uma árvore de diretórios representando os setores e criar um arquivo `.md` para cada via. O arquivo gerado SHALL ser pré-preenchido com dados lidos do banco de dados e SHALL conter blocos de formulário (checklists) formatados para fácil edição móvel (listas aninhadas).

#### Scenario: Script iterador gera a árvore de diretórios e os arquivos das vias
- **WHEN** o script de geração de fichas for executado apontando para a base da Lapinha
- **THEN** o script itera sobre a pasta de origem `database/br_mg_lagoa_santa_gruta_da_lapinha` lendo os arquivos `.yaml`
- **THEN** para cada via encontrada, cria (se não existir) a pasta do seu respectivo setor na pasta de output
- **THEN** gera o arquivo no formato `<id_da_via>_<nome_formatado_da_via>.md` contendo a avaliação em branco.

#### Scenario: Preenchimento do Markdown com metadados do BD
- **WHEN** o arquivo Markdown da via é gerado
- **THEN** no topo do arquivo as chaves (ex: Data de conquista, Conquistadores, Data última manutenção) correspondentes aos dados existentes no YAML original são preenchidas para servirem de contexto.

#### Scenario: Geração da estrutura de checkboxes aninhados
- **WHEN** o arquivo Markdown da via é gerado
- **THEN** a seção "Informações Gerais" é inserida contendo listas aninhadas em markdown para itens como (Tipo da Via, Estado parada no topo, etc).
- **THEN** seções de repetição chamadas "Top Rope 1", "Top Rope 2", e "Proteção 1" até "Proteção 16" são adicionadas em loop, incluindo opções aninhadas (Tipo, Estado) prontas para serem marcadas com checkboxes (`[ ]`) no aplicativo móvel, e cabeçalhos textuais em negrito para facilitar o parsing futuro.
