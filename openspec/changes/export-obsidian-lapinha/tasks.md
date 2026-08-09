## 1. Setup e Leitura Base

- [x] 1.1 Criar arquivo de script Python `scripts/gerar_fichas_lapinha.py`.
- [x] 1.2 Implementar rotina para ler todos os arquivos `.yaml` iterativamente dentro de `database/br_mg_lagoa_santa_gruta_da_lapinha`.
- [x] 1.3 Implementar a criação da árvore de subdiretórios de saída (por exemplo, dentro de uma nova pasta `export/obsidian/lapinha/<setor>`).

## 2. Motor de Templates Markdown

- [x] 2.1 Escrever o construtor do bloco superior do arquivo (`## Dados da via`), lendo metadados (nome, conquista, manutenção, conquistadores) do YAML da via respectiva.
- [x] 2.2 Escrever o construtor da seção estática de checklist `## 📋 Informações Gerais (preencher)`.
- [x] 2.3 Escrever o loop construtor das proteções iterando para injetar `## Top Rope 1`, `## Top Rope 2`, e `## Proteção 1` até `## Proteção 16`, juntamente com as opções aninhadas `- [ ]`.
- [x] 2.4 Unir os construtores em um único buffer e gravar o conteúdo no arquivo `<id_da_via>_<nome>.md` na pasta correspondente.

## 3. Validação Final

- [x] 3.1 Rodar o script e garantir que ele executa sem erros em toda a base da Lapinha.
- [x] 3.2 Inspecionar visualmente os arquivos gerados `.md` e confirmar que a sintaxe de listas aninhadas e checkboxes está íntegra (renderiza corretamente num leitor de markdown).
