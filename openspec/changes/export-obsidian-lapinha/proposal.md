## Why

O usuário precisa de um formato prático, off-line e editável no celular para coletar dados de campo durante a inspeção estrutural de vias de escalada na Gruta da Lapinha. O Obsidian será usado como ferramenta principal devido à sua robustez offline. Precisamos exportar os dados atuais do banco de dados `aresta_db` (arquivos YAML) para notas formatadas em Markdown contendo uma estrutura rigorosa (formulário) baseada em listas de opções para facilitar o preenchimento no celular (checklists com áreas de toque grandes) e possibilitar a futura ingestão automática dos dados de volta para o banco de dados.

## What Changes

- Criação de um script em Python (ex: `gerar_fichas_lapinha.py`) capaz de iterar pela base de dados da Lapinha.
- O script gerará uma estrutura de diretórios baseada nos setores (ex: `setor_1`, `setor_2`).
- Para cada via, um arquivo Markdown correspondente será criado, contendo:
  - Dados pré-preenchidos da via (Nome, Data de conquista, Data última manutenção, Conquistadores).
  - Listas de opções (em formato de bullet points markdown com `[ ]`) para Informações Gerais e características de cada proteção, com suporte para até 16 proteções intermediárias + paradas Top Rope 1 e 2.
- A padronização da estrutura do arquivo Markdown vai permitir a futura extração das anotações usando regex ou scripts de parser.

## Capabilities

### New Capabilities
- `exportacao-obsidian-fichas`: Funcionalidade de leitura dos arquivos YAML estruturados e geração de templates padronizados em Markdown contendo layouts parseáveis e pré-preenchidos com dados da base.

### Modified Capabilities
- (Nenhuma)

## Impact

- Criação de um novo script utilitário (a ser definido na pasta correspondente, possivelmente na raiz ou `scripts/`).
- Geração de uma pasta de saída (`export/obsidian/lapinha` ou similar) contendo as fichas prontas para serem movidas para o celular.
- Nenhuma alteração no schema do `aresta_db`.
