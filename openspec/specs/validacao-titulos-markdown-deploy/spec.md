# validacao-titulos-markdown-deploy Specification

## Purpose

Define a validação contra cabeçalhos H1 na descrição de setores e grupos durante o deploy de croquis, além de estabelecer a padronização do campo de nome de setores no frontmatter.

## Requirements

### Requirement: Alerta de cabeçalho H1 em descrição de setor e grupo no deploy
O pipeline de deploy SHALL verificar se a descrição Markdown de qualquer setor ou grupo contém cabeçalhos H1 (linhas iniciando com `# `) e emitir um aviso informativo caso encontrado, sem interromper o processo de compilação.

#### Scenario: Setor com H1 na descrição emite aviso no deploy
- **WHEN** o script `deploy_generated.py` compila um croqui contendo um setor cuja descrição possui `# Setor Exemplo`
- **THEN** o sistema emite um aviso no console informando que o setor contém cabeçalho H1 redundante e conclui a compilação normalmente

#### Scenario: Setor sem H1 na descrição compila sem alertas de título
- **WHEN** o script `deploy_generated.py` compila um croqui contendo setores com texto livre ou subtítulos (`## Acesso`) sem nenhum `# ` (H1)
- **THEN** o sistema não emite nenhum aviso de cabeçalho H1

### Requirement: Padronização de prefixos no nome de setores
O banco de dados SHALL padronizar os nomes de setores no YAML Frontmatter com o prefixo 'Setor ', mantendo o prefixo 'Bloco ' para blocos de boulder e preservando os nomes de grupos sem prefixação forçada.

#### Scenario: Setor sem prefixo recebe prefixo Setor
- **WHEN** a rotina de saneamento processa um arquivo de setor cujo `nome` é "Achados e Perdidos"
- **THEN** o campo `nome` no YAML Frontmatter é atualizado para "Setor Achados e Perdidos"

#### Scenario: Bloco de boulder preserva o prefixo Bloco
- **WHEN** a rotina de saneamento processa um arquivo de setor cujo `nome` é "Bloco 45º"
- **THEN** o campo `nome` permanece como "Bloco 45º" sem adição do prefixo "Setor "

#### Scenario: Grupo preserva seu nome original
- **WHEN** a rotina de saneamento processa um arquivo de grupo cujo `nome` é "Vale Oculto"
- **THEN** o campo `nome` permanece inalterado como "Vale Oculto"

### Requirement: Remoção de H1 redundante no corpo do Markdown
A rotina de migração e saneamento SHALL remover a linha de título H1 do corpo Markdown de setores e grupos, esvaziando o corpo caso ele contenha unicamente o cabeçalho.

#### Scenario: Corpo com H1 e texto explicativo
- **WHEN** um arquivo de setor possui `# Setor Bem-vindo` seguido por um parágrafo descritivo
- **THEN** a linha do cabeçalho H1 e espaços em branco iniciais são removidos, preservando o parágrafo descritivo no corpo

#### Scenario: Corpo contendo exclusivamente o H1
- **WHEN** um arquivo de setor possui apenas `# Setor Achados e Perdidos` no corpo Markdown
- **THEN** o corpo Markdown é esvaziado, evitando seções de descrição vazias na UI
