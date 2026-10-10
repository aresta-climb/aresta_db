# Design

## Context

No pipeline de deploy (`scripts/deploy_generated.py`), o Passo A compila cada croqui e executa verificações de integridade (`verificar_nomes_duplicados_de_escalada`, `verificar_mapas_duplicados`, etc.). Atualmente, nenhuma verificação analisa a presença de cabeçalhos no Markdown de descrição de setores e grupos.

Na base atual (`database/`), aproximadamente 400 arquivos possuem cabeçalhos `# H1` no corpo Markdown que apenas repetem o nome do setor ou grupo, gerando duplicação visual no aplicativo. Além disso, o campo `nome:` no frontmatter de setores está inconsistente entre arquivos (alguns com "Setor ", alguns com "Bloco ", e centenas sem prefixo).

## Goals / Non-Goals

**Goals:**
- Implementar a rotina de validação `verificar_titulos_em_descricao_setor_grupo` em `scripts/deploy_generated.py`.
- Desenvolver um script utilitário de migração/saneamento testável e idempotente (`scripts/migrar_titulos_e_nomes_setores.py`) para higienizar a base de dados.
- Padronizar o campo `nome:` de setores para conter o prefixo "Setor " (mantendo "Bloco " para blocos de boulder).
- Manter nomes de grupos inalterados (sem imposição de prefixo "Grupo ").
- Remover o H1 do corpo Markdown de setores e grupos, deixando o corpo vazio quando não houver outro conteúdo.
- Atualizar a skill `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`.
- Garantir 100% de cobertura de testes unitários conforme os princípios do repositório (AGENTS.md).

**Non-Goals:**
- Não alterar nem proibir subtítulos legítimos de nível 2 ou inferior (ex: `## Acesso`, `## Como Chegar`).
- Não alterar arquivos Markdown que não representem setores ou grupos (ex: `capa.md`, `introducao.md`, `acesso.md`).
- Não quebrar ou modificar o comportamento de campos do Protobuf.

## Decisions

### 1. Detecção do Warning no `deploy_generated.py`
A verificação será adicionada ao Passo A do deploy, inspecionando os dados compilados (`compiled_data`) após a geração do YAML:
- Percorre recursivamente todos os setores e grupos de cada pico.
- Para cada entidade que possui o campo `descricao`, procura por linhas que comecem com `# ` (cabeçalho H1 Markdown).
- Caso encontre, emite um aviso no console seguindo a formatação padrão do script (`Aviso: A descrição do setor '{nome}'...`).
- O deploy não falha; o aviso é estritamente informativo para manter compatibilidade com o fluxo existente de alertas.

*Alternativa considerada*: Validar diretamente os arquivos `.md` antes da compilação.  
*Razão da escolha*: Validar no `compiled_data` cobre tanto arquivos `.md` referenciados quanto setores/grupos embutidos diretamente no `croqui.yaml`.

### 2. Regras de Saneamento e Migração
O script de migração processará os arquivos `.md` de setores e grupos:
1. **Recuperação de Nome Ausente**: Se o frontmatter não tiver o campo `nome:`, ele é recuperado a partir do H1 limpo (removendo eventuais `# `, `Setor `, etc.).
2. **Prefixação de Setores**:
   - Se o arquivo for de setor e `nome:` não começar com `"Setor "` nem com `"Bloco "`, adiciona `"Setor "`.
   - Se já começar com `"Setor "` ou `"Bloco "`, preserva.
3. **Preservação de Grupos**:
   - Se o arquivo for de grupo, preserva o `nome:` existente sem adicionar `"Grupo "`.
4. **Remoção de H1 do Corpo**:
   - Remove qualquer linha que comece com `# ` (H1).
   - Remove linhas em branco residuais no início do corpo.
   - Se o corpo resultante consistir unicamente de espaços em branco, ele se torna string vazia.
   - Regrava o arquivo utilizando `salvar_md_com_frontmatter`.

*Alternativa considerada*: Fazer a limpeza silenciosa durante o próprio `corrigir_database` a cada deploy.  
*Razão da escolha*: Uma migração pontual e explícita permite revisar os diffs de uma só vez, deixando o `deploy_generated.py` apenas como guardião/aviso para prevenir regressões dali em diante.

## Risks / Trade-offs

- **[Risco] Modificação em massa de ~400 arquivos no banco de dados.**  
  *Mitigação*: O script utilitário de migração será desenvolvido primeiro via TDD com cobertura exaustiva de casos de borda em testes unitários. A execução no banco será validada com `git diff` e execução completa da suíte de testes e do deploy de teste.

- **[Risco] Possível quebra de referências de mapas.**  
  *Mitigação*: Foi verificado no banco que as referências em mapas apontam para `alvo_uid` ou para escaladas individuais (`escalada:`), não existindo referências nominais de setores nos mapas atuais.
