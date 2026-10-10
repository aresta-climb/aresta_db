# Tasks

## 1. Verificação e Alerta de H1 no Deploy

- [x] 1.1 Escrever testes unitários em `scripts/deploy_generated_test.py` cobrindo a detecção de cabeçalhos H1 na descrição de setores e grupos (com H1, sem H1, com H2 permitido) e verificar que falham inicialmente (RED)
- [x] 1.2 Implementar a função `verificar_titulos_em_descricao_setor_grupo` em `scripts/deploy_generated.py` e integrá-la no Passo A de compilação, verificando que os testes passam (GREEN)
- [x] 1.3 Garantir 100% de cobertura de testes para a nova verificação executando `pytest scripts/deploy_generated_test.py`

## 2. Utilitário de Migração e Saneamento da Base

- [x] 2.1 Criar a suíte de testes unitários `scripts/migrar_titulos_e_nomes_setores_test.py` cobrindo todas as regras de transformação (adição de "Setor ", preservação de "Bloco ", preservação de grupos, remoção de H1, recuperação de nome ausente e esvaziamento de corpo) e verificar que falham inicialmente (RED)
- [x] 2.2 Implementar o módulo e CLI `scripts/migrar_titulos_e_nomes_setores.py` de forma pura e idempotente, verificando que todos os testes passam (GREEN)
- [x] 2.3 Garantir 100% de cobertura de testes unitários no novo script executando `pytest --cov=scripts.migrar_titulos_e_nomes_setores scripts/migrar_titulos_e_nomes_setores_test.py`

## 3. Execução da Migração no Banco e Validação de Integridade

- [x] 3.1 Executar a migração sobre todo o diretório `database/` através de `python scripts/migrar_titulos_e_nomes_setores.py` e inspecionar os diffs gerados
- [x] 3.2 Executar a compilação do deploy via `python scripts/deploy_generated.py` validando que todos os croquis compilam com sucesso e nenhum aviso de título H1 é disparado

## 4. Atualização de Instruções de Agentes

- [x] 4.1 Atualizar o arquivo `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` inserindo a regra explícita que proíbe títulos H1 no corpo Markdown de setores e grupos e reforça a prefixação correta no frontmatter
