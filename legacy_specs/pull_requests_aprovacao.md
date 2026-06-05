## Especificação Técnica: Controle Restrito de Diretórios e Automação de Merge

### Objetivo
Garantir que usuários específicos tenham autoridade exclusiva e automatizada para aprovar e integrar Pull Requests (PRs) restritos a um determinado diretório, sem conceder a eles permissão de edição (Write) no repositório geral. A intervenção manual de desenvolvedores globais só será exigida se o PR alterar arquivos fora do escopo restrito.

### 1. Definição de Acessos (RBAC)

A separação de permissões é a base de segurança desta implementação.

* **Aprovadores Restritos:** Devem receber exclusivamente permissão de **Read** (Leitura) no repositório. Isso impede que alterem código diretamente ou aprovem PRs fora de sua jurisdição com peso de integração.
* **Desenvolvedores Globais:** Mantêm permissões de **Write**, **Maintain** ou **Admin**.

### 2. Configurações Globais do Repositório

É necessário preparar o repositório para aceitar ações automatizadas e integrações assíncronas.

1. Navegue até **Settings** > **General**.
2. Na seção **Pull Requests**, marque a opção **Allow auto-merge**.
3. Navegue até **Settings** > **Actions** > **General**.
4. Em **Workflow permissions**, selecione **Read and write permissions**.
5. Marque a caixa **Allow GitHub Actions to create and approve pull requests**.

### 3. Proteção de Branch (Branch Protection)

Esta configuração força o GitHub a respeitar o arquivo de propriedade de código antes de qualquer integração.

1. Navegue até **Settings** > **Branches**.
2. Adicione ou edite a regra para a branch principal (ex: `main`).
3. Habilite **Require a pull request before merging**.
4. Habilite **Require review from Code Owners**.

### 4. Mapeamento de Propriedade (CODEOWNERS)

O arquivo de configuração define quem é exigido para a revisão de cada caminho. Crie o arquivo `.github/CODEOWNERS` na raiz do projeto.

```text
# 1. Fallback Global: Exige aprovação dos desenvolvedores globais para qualquer arquivo
* @aresta_db/owners

# 2. Exceção do Diretório: Exige aprovação dos usuários restritos OU dos globais
# O uso de usuários individuais (e não times) é obrigatório para contas com acesso 'Read'
/pasta-restrita/ @usuario-restrito @aresta_db/owners
```

---

### 5. Automação de Auto-Merge (GitHub Actions)

Para remover a necessidade de um usuário "Write" clicar no botão de habilitar o auto-merge a cada novo PR que só atualiza croquis, este workflow fará a ativação imediata via CLI assim que um PR for aberto e se esse PR afetar apenas diretórios na subpasta `database`. Caso afete outros diretórios, ele não será habilitado para auto-merge e precisará da aprovação de um desenvolvedor global.

Crie o arquivo `.github/workflows/enable-automerge.yml`:

```yaml
name: Habilitar Auto-Merge Restrito
on:
  pull_request:
    types: [opened, ready_for_review, reopened, synchronize]

jobs:
  enable-auto-merge:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read # Necessário para o GitHub CLI ler os metadados do PR
      
    steps:
      - name: Checkout do código
        uses: actions/checkout@v4

      - name: Validar pastas e ligar Auto-merge
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_URL: ${{ github.event.pull_request.html_url }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          # 1. Defina aqui as pastas permitidas (mantenha a barra / no final)
          ALLOWED_DIRS=("database/")
          
          echo "Verificando arquivos alterados no PR #$PR_NUMBER..."
          
          IS_VALID=true
          
          # 2. Lê cada arquivo alterado listado pelo GitHub CLI
          while read -r file; do
            FILE_ALLOWED=false
            
            # Verifica se o arquivo começa com o caminho de alguma pasta permitida
            for dir in "${ALLOWED_DIRS[@]}"; do
              if [[ "$file" == "$dir"* ]]; then
                FILE_ALLOWED=true
                break
              fi
            done
            
            # Se achar UM arquivo que não bate com as pastas permitidas, aborta a validação
            if [ "$FILE_ALLOWED" = false ]; then
              echo "⚠️ Alteração bloqueada para auto-merge: O arquivo '$file' está fora do escopo."
              IS_VALID=false
              break
            fi
          done <<< "$(gh pr view $PR_NUMBER --json files --jq '.files[].path')"
          
          # 3. Executa a decisão final
          if [ "$IS_VALID" = true ]; then
            echo "✅ Todos os arquivos estão nas pastas autorizadas. Habilitando auto-merge..."
            gh pr merge --auto --squash "$PR_URL"
          else
            echo "❌ PR contém alterações globais. O Auto-merge não será habilitado."
            exit 0  # Sai sem erro, apenas aborta o auto-merge.
            # Opcional: Se quiser que o workflow falhe visualmente com um X vermelho
            # exit 1 
          fi
```

### 6. Fluxo de Execução Esperado

O comportamento do sistema após a implementação completa seguirá estas regras lógicas:

* **Cenário A (PR apenas na pasta restrita):** O PR é aberto. A Action ativa o auto-merge. O `@usuario-restrito` revisa e aprova. O GitHub realiza o merge automaticamente de forma instantânea.
* **Cenário B (PR em outras pastas):** O PR é aberto. A Action não ativa o auto-merge. O GitHub aguarda a aprovação de `@aresta_db/owners`. O desenvolvedor global precisa executar o merge.
* **Cenário C (PR misto):** O PR é aberto. A Action não ativa o auto-merge. O GitHub bloqueia a integração e exige, obrigatoriamente, a aprovação de pelo menos um desenvolvedor global para liberar o código. A aprovação isolada do usuário restrito não será suficiente para engatilhar o merge. O desenvolvedor global precisa executar o merge.

### 7. Auto-aprovação dinâmica baseada em CODEOWNERS

O objetivo é eliminar gargalos de revisão manual em Pull Requests onde o autor da alteração já é o proprietário (Code Owner) de todos os arquivos modificados. Um Bot será utilizado como "proxy" para conceder a aprovação necessária, satisfazendo as regras de proteção da branch sem violar a restrição do GitHub de auto-aprovação.

#### 7.1. Regra de Negócio (Lógica de Validação)
Para que o Pull Request seja aprovado automaticamente pelo Bot, a seguinte condição booleana deve ser **verdadeira**:
* O nome de usuário do autor do PR deve constar como proprietário resolvido no arquivo `.github/CODEOWNERS` para **cada um dos arquivos** listados nas alterações do PR.
* Se houver a modificação de **um único arquivo** onde o autor do PR não for o proprietário designado, a automação é abortada e a revisão de pares padrão é exigida.

#### 7.2. Configuração de Autoridade do Bot (Crucial)
Como o GitHub exige que a aprovação venha de um `CODEOWNER` válido, o Bot que fará a auto-aprovação precisa ter autoridade sobre os arquivos. 
* Adicione a conta de serviço do Bot (uma conta fantasma criada para esse fim, com permissões de escrita no repositório) como um proprietário global ou como coproprietário em todas as regras do `CODEOWNERS`. Basicamente, será parte de `@aresta_db/owners`.

### 7.3. Especificação do Workflow (GitHub Actions)
O workflow será acionado quando o PR for aberto ou sincronizado. Ele utilizará um script para mapear a propriedade.

**Caminho:** `.github/workflows/codeowner-auto-approve.yml`

```yaml
name: Auto-Aprovação por Propriedade (CODEOWNERS)
on:
  pull_request:
    types: [opened, ready_for_review, reopened, synchronize]

jobs:
  validate-and-approve:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      
    steps:
      - name: Checkout do repositório
        uses: actions/checkout@v4

      - name: Validar Propriedade e Aprovar
        env:
          # O token do usuário máquina (Bot) configurado como secret
          GITHUB_TOKEN: ${{ secrets.TOKEN_DE_APROVACAO_BOT }}
          PR_AUTHOR: ${{ github.event.pull_request.user.login }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          PR_URL: ${{ github.event.pull_request.html_url }}
        run: |
          echo "Autor do PR: $PR_AUTHOR"
          
          # 1. Recupera todos os arquivos alterados no PR
          FILES=$(gh pr view $PR_NUMBER --json files --jq '.files[].path')
          
          # 2. Utiliza script Python para ler e resolver o arquivo CODEOWNERS
          # (O Python consegue lidar melhor com a precedência e regex do arquivo)
          python3 .github/scripts/check_codeowners.py "$PR_AUTHOR" "$FILES"
          RESULT=$?
          
          # 3. Toma a decisão com base na saída do script
          if [ $RESULT -eq 0 ]; then
            echo "✅ Cobertura total confirmada. O autor é o dono de todos os arquivos."
            echo "Realizando aprovação proxy..."
            gh pr review "$PR_URL" --approve --body "🤖 PR aprovado automaticamente. O autor '$PR_AUTHOR' é o proprietário designado de todos os arquivos modificados neste PR."
          else
            echo "⚠️ Cobertura insuficiente. O autor não é dono de todos os arquivos modificados. Aprovação manual necessária."
            exit 0 # Sai sem erro, apenas aborta a aprovação
          fi
```

### 7.4. Ordem de Execução na Esteira (CI/CD)
Para garantir a segurança do banco de dados e da branch principal, este processo deve coexistir com as execuções de testes:
1. O desenvolvedor abre o PR.
2. A Action de Auto-Aprovação mapeia os `CODEOWNERS`. Se for 100% do autor, o Bot envia a review `Approve`.
3. Em paralelo, as Actions de Testes Unitários e Testes de Integração são iniciadas.
4. O Auto-Merge (se configurado) **aguardará em estado pendente** (pending).
5. Apenas quando as Actions de Testes ficarem verdes (`success`), o GitHub efetuará o merge automático, blindando o repositório.