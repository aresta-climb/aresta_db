## 1. Preparação

- [ ] 1.1 Criar o script Python temporário para leitura do CSV e processamento.
- [ ] 1.2 Implementar a lógica de parse seguro de Markdown + YAML Frontmatter.

## 2. Lógica de Merge

- [ ] 2.1 Mapear o CSV, extraindo a coluna `N°` (ID) e `Ano`.
- [ ] 2.2 Percorrer cada arquivo `setor_mapa_X.md` no diretório da Lapinha.
- [ ] 2.3 Utilizar os IDs presentes na chave `referencias` do YAML para associar a via com o dado do CSV.
- [ ] 2.4 Injetar a propriedade `data_abertura` na via dentro de `escaladas` se ela existir no CSV.
- [ ] 2.5 Preservar a string `nome` original do YAML independentemente de eventuais divergências no CSV.

## 3. Validação

- [ ] 3.1 Executar o script no modo dry-run para verificar as modificações no terminal (opcional).
- [ ] 3.2 Executar o script sobrescrevendo os arquivos e conferir a sintaxe YAML gerada.
- [ ] 3.3 Rodar a compilação do banco de dados da Aresta para garantir que a inserção não quebrou nada.
