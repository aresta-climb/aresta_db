## Context

O Aresta precisa suportar a capacidade de rascunhar croquis antes de sua publicação definitiva. Atualmente, qualquer croqui adicionado na pasta `database` e compilado pelo `deploy_generated.py` entra imediatamente no índice `indice.binarypb` e é exposto para todos os usuários em produção. 

## Goals / Non-Goals

**Goals:**
- Permitir que editores construam croquis aos poucos e testem essas edições localmente (via Aresta App usando as APIs geradas localmente).
- Evitar o vazamento de croquis inacabados para o público através do índice de produção.
- Manter a compatibilidade com todos os croquis "revisados" da base de dados atual através de uma migração inicial.

**Non-Goals:**
- Proteger o conteúdo (arquivos compilados) de acesso direto. O Aresta é um projeto open-source e open-data; se alguém conhecer a URL de um rascunho em `/generated/<id>`, poderá baixá-lo. O objetivo é apenas não listá-lo no índice.
- Controle de versão complexo (draft, in-review, published, etc.). Apenas um sinalizador (flag) booleano atende à necessidade inicial.

## Decisions

1. **Utilização da flag `--producao` no `deploy_generated.py`**
   - **Decisão:** Adicionar `--producao` (padrão) e `--no-producao` via `argparse.BooleanOptionalAction`.
   - **Justificativa:** Centraliza no script de deploy a decisão final do que vai para o índice. O Github Actions utilizará o default (produção), enquanto o script `croqui_experimental.py` (usado pelo editor) forçará `is_producao=False` via código para que os editores continuem vendo croquis não publicados no App de preview local.

2. **Campo `publicar_croqui` em `croqui.proto`**
   - **Decisão:** Usar `bool publicar_croqui = 16`.
   - **Justificativa:** É mais descritivo e alinhado com a ação do usuário na UI. Embora uma flag negativa como "rascunho" evitasse migrações (já que proto3 inicializa booleanos em `false`), adotar "publicar" evita acidentes com futuros croquis recém-criados indo para produção indevidamente e atende exatamente o escopo discutido com os stakeholders.

3. **Script de Migração baseada em `revisado_manualmente`**
   - **Decisão:** Fazer um script one-off que marcará `publicar_croqui = True` e salvará no YAML somente quando o croqui atual possuir `revisado_manualmente == True`.
   - **Justificativa:** Garante transição imediata mantendo a estabilidade de qualidade. Croquis da branch principal sem revisão manual validada não vazarão para produção, o que condiz com o zelo pela qualidade das informações servidas.

## Risks / Trade-offs

- **[Risk] Todos os croquis atuais vão sumir da produção se o deploy rodar antes do script de migração.** 
  → **Mitigation:** O script de migração deve ser escrito e executado *antes* do deploy com a nova feature, gerando um commit com as atualizações de yaml.
- **[Risk] Alguns croquis expostos no ambiente de produção sumirão da lista, pois não tinham `revisado_manualmente: true`.**
  → **Mitigation:** O "downgrade" (remoção dos que não estão marcados como revisados) foi aceito explicitamente no requisito como um ganho sistêmico, filtrando a exibição apenas para o que foi verificado. O mantenedor poderá habilitar manualmente os despublicados caso queira.
