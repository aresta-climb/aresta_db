# Design: Isolamento de Staging e Transparência na Submissão de PR

## Context

O Aresta Editor Desktop utiliza a biblioteca `ServicoSubmissao` (`editor/core/servico_submissao.py`) e `pygit2` para:
1. Criar branch de proposta (`edicao-<id_croqui>-<uuid8>`) baseada no commit upstream mais recente.
2. Espelhar os arquivos do croqui de trabalho para `database/<id_croqui>/` no repositório base local.
3. Adicionar os arquivos ao `index` do Git e gravar a árvore (`index.write_tree()`).
4. Criar o commit assinado e enviá-lo via Git Proxy.
5. Invocar a Edge Function `create-pr` no Supabase para formalizar a Pull Request.

Conforme detalhado no `proposal.md`, a chamada a `index.write_tree()` sem a reinicialização explícita do `index` a partir da árvore de `head_commit` faz com que quaisquer arquivos previamente alterados ou sujos no repositório local (fora de `database/<id_croqui>/`) sejam persistidos no commit, disparando rejeição com HTTP 400 pelo validador de escopo do backend.

## Goals / Non-Goals

**Goals:**
- Garantir que o commit gerado por `criar_commit_sugestao` contenha estritamente e exclusivamente alterações na pasta `database/<id_croqui>/`.
- Garantir que arquivos deletados dentro de `database/<id_croqui>/` sejam expurgados corretamente do índice do commit.
- Repassar e formatar os `arquivos_invalidos` retornados pelo servidor no erro gerado pelo `ServicoSubmissao`.
- Manter 100% de cobertura de testes unitários com TDD e aderência às regras do repositório (`AGENTS.md`).

**Non-Goals:**
- Não alterar a arquitetura do Git Proxy ou da autenticação Supabase/GitHub.
- Não introduzir dependências externas adicionais; operar estritamente com `pygit2` e bibliotecas padrão.
- Não modificar o fluxo de merge ou de sincronização de conflitos remotos existente.

## Decisions

### Decisão 1: Reset do `Index` com `read_tree(head_commit.tree_id)` antes do Staging
- **Abordagem**: No início de `criar_commit_sugestao`:
  ```python
  head_commit = cast(pygit2.Commit, repo.head.peel())
  index = repo.index
  index.read_tree(head_commit.tree_id)
  ```
  Isso redefine em memória todas as entradas do índice para ficarem idênticas à árvore do commit base, descartando qualquer sujeira residual ou arquivos fora de escopo.
- **Alternativas consideradas**:
  - *Construir árvore manualmente com `TreeBuilder`*: Excessivamente complexo para árvores com múltiplos subdiretórios (`imagens/`, `anexos/`).
  - *Executar `git reset --hard` no diretório de trabalho*: Inseguro, pois descartaria arquivos de trabalho e aumentaria o acoplamento com o filesystem.
  - *`index.read_tree`*: Simples, nativo do libgit2/pygit2, atômico e in-memory.

### Decisão 2: Remoção Explícita de Arquivos Deletados no Croqui
- **Abordagem**: Após `index.read_tree` e `index.add_all([caminho_relativo])`, inspecionar as entradas do índice que iniciam com `caminho_relativo + "/"` e remover do índice (`index.remove(entry.path)`) qualquer arquivo que não exista mais fisicamente no diretório `database/<id_croqui>/`.
- **Justificativa**: O método `index.add_all()` lida primordialmente com adições e modificações. A checagem explícita garante que exclusões intencionais de fotos ou arquivos `.md` sejam refletidas com precisão no commit.

### Decisão 3: Extração e Exibição de `arquivos_invalidos`
- **Abordagem**: Em `ServicoSubmissao.solicitar_abertura_pr`:
  Ao receber código de status HTTP diferente de 200:
  ```python
  dados_erro = resposta.json()
  msg = dados_erro.get("erro", resposta.text)
  arquivos_invalidos = dados_erro.get("arquivos_invalidos")
  if arquivos_invalidos:
      msg += "\n\nArquivos fora do escopo permitidos:\n" + "\n".join(f"• {arq}" for arq in arquivos_invalidos)
  elif arquivos_invalidos == []:
      msg += "\n\n(Nenhum arquivo modificado foi detectado pelo servidor na branch)."
  ```
- **Justificativa**: Oferece visibilidade imediata ao colaborador sobre o motivo exato da recusa sem necessidade de inspeção manual de logs de servidor.

## Risks / Trade-offs

- **[Risco]** Arquivos não salvos ou modificados no repositório base local sendo perdidos no commit.
  - *Mitigação*: O repositório base local do aplicativo serve unicamente como espelho da base oficial; todo o trabalho do usuário reside na pasta experimental `croquis/<id>/`. O isolamento do staging protege a integridade do commit oficial.
- **[Risco]** Impacto em performance da leitura da árvore com `index.read_tree`.
  - *Mitigação*: A operação no `pygit2` é em memória C (libgit2) e leva menos de 5ms para árvores com milhares de arquivos.
