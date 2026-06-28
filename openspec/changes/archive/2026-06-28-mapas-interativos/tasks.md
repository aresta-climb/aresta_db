## 1. Protobuf (`croqui.proto`)

- [x] 1.1 Adicionar mensagem `ColecaoDeMapas` com `repeated Mapa mapas`.
- [x] 1.2 Adicionar mensagem `ArquivoMapas` e encapsular o `oneof` (usando `ONEOF_CONTEUDO` conforme princípios).
- [x] 1.3 Adicionar campo `ArquivoMapas mapas_gerais = 12` em `Pico`.
- [x] 1.4 Compilar proto (`scripts/compilar_proto.bat`).

## 2. Editor de Croquis (TDD)

- [x] 2.1 Criar testes de unidade/integração falhos para a renderização de `ArquivoMapas` e sua inclusão na árvore do editor de dados para o `Pico`.
- [x] 2.2 Implementar a lógica na UI (`editor/views/`) para injetar a edição do mapa no arquivo isolado, fazendo os testes passarem.
- [x] 2.3 Refatorar garantindo 100% de cobertura no componente afetado.

## 3. Scripts de Processamento (TDD)

- [x] 3.1 Criar testes de unidade falhos para o suporte ao `mapas_gerais.md` no `preparar_extracao_de_mapas.py` e `finalizar_mapas.py`.
- [x] 3.2 Atualizar `preparar_extracao_de_mapas.py` incluindo o globbing para `mapas_gerais.md`, e garantindo aprovação nos testes.
- [x] 3.3 Atualizar `finalizar_mapas.py` validando o comportamento de arquivos exclusivamente com frontmatter, garantindo aprovação nos testes.
- [x] 3.4 Avaliar coverage e refatorar se necessário para atingir 100% nessas funções.

## 4. Migração de Dados (TDD)

- [x] 4.1 Extrair a lógica de conversão de Markdown com texto para Markdown apenas com Frontmatter (`mapas:`) em uma biblioteca isolada (Library-First).
- [x] 4.2 Criar testes de unidade exaustivos com mocks do `croqui.yaml` e `mapas_gerais.md` para a lógica de migração.
- [x] 4.3 Implementar a lógica de migração pura (Red-Green-Refactor).
- [x] 4.4 Envolver a lógica testada no runner do script `migracoes/0003_migrar_mapas_gerais.py`.
- [x] 4.5 Executar a migração 0003 em todo o banco real.

## 5. Agentes de IA

- [x] 5.1 Modificar `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` para rotular explicitamente a seção como `mapas_gerais`.
- [x] 5.2 Modificar `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` instruindo a geração exclusiva do frontmatter `ColecaoDeMapas`.
