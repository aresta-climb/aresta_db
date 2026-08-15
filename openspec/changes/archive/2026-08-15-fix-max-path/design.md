## Context

O empacotamento MSIX cria um caminho virtualizado (`.../LocalCache/Roaming/...`) longo para o `AppData` do aplicativo. No Windows, o limite tradicional é de 260 caracteres (`MAX_PATH`). A estrutura atual de pastas superava isso ao concatenar caminhos gerados pelo Qt com caminhos duplicados da nossa aplicação, e adicionando strings baseadas nos nomes das montanhas, resultando no crash `WinError 206`.

## Goals / Non-Goals

**Goals:**
- Reduzir permanentemente a profundidade da estrutura de diretórios de dados locais (removendo subpastas duplicadas e nomes longos desnecessários na raiz).
- Habilitar o suporte do sistema operacional Windows (via MSIX) para que tolere caminhos maiores que 260 caracteres quando estritamente necessário.
- Garantir que a sincronização Git (`pygit2`) faça uso de configurações tolerantes a caminhos longos antes de iniciar transferências pesadas.

**Non-Goals:**
- Criar rotinas automáticas de migração para croquis locais na máquina dos desenvolvedores criados antes deste patch. (Como a versão nunca foi lançada, dados experimentais antigos podem ser deletados/refeitos localmente se quebrarem).
- Remover o suporte a projetos de múltiplos usuários se existirem no futuro, a mudança foca puramente nos caminhos estáticos da API do Qt.

## Decisions

1. **Definição Explícita de Nome do App no Qt**
   - **Por que?** Evita a variação do nome da pasta em tempo de execução (que antes causava a criação da subpasta redundante `EditorAresta/aresta_editor`). Ao invocar `QCoreApplication.setApplicationName("EditorAresta")` na inicialização, todos os locais de dados base serão previsíveis.

2. **IDs de 8 Caracteres Hex (UUID4)**
   - **Por que?** Substitui a lógica de `timestamp_nome_completo` para o nome físico da pasta do projeto. O nome amigável do croqui existe nos metadados (`croqui.yaml`), portanto, a pasta em si ser `9aecd32d` não interfere no UI, mas corta radicalmente dezenas de caracteres do `MAX_PATH`. Para mitigar a opacidade, o UI passará a renderizar esse ID explicitamente, e ordenará a listagem pelo tempo de edição (lido dos arquivos YAML).

3. **Virtualização do AppData pelo MSIX**
   - **Por que não forçar um path customizado (ex: C:\Users\nome\EditorAresta) para fugir do MSIX?** O Windows 10/11 utiliza a virtualização do AppData (`LocalCache\Roaming`) em aplicativos empacotados (AppX/MSIX) como medida de segurança e higiene do sistema (permitindo desinstalações 100% limpas que não deixam lixo no registro ou no disco do usuário). Lutar contra a virtualização exige capacidades restritas (`broadFileSystemAccess`) que muitas vezes geram atritos na aprovação da Microsoft Store. Ao encurtarmos a árvore de diretórios do nosso lado, nós cooperamos com a virtualização do SO (que já gasta ~110 caracteres) e evitamos o `MAX_PATH` de forma "Store-friendly".

4. **`pygit2.init_repository` com Injeção Direta**
   - **Por que?** `clone_repository` é uma abstração de alto nível. Nós o substituiremos pelo fluxo manual: `init_repository` -> `repo.config['core.longpaths'] = True` -> `fetch` -> `checkout`. Isso atua como um escudo protetor para o motor do Git durante o download.

## Risks / Trade-offs

- **[Risco] Opacidade no disco local** → Sem o nome da montanha na pasta, depuração via Explorador de Arquivos fica menos intuitiva. 
  - **Mitigação**: Desenvolvedores usarão a interface do Editor Aresta que decodifica as pastas usando seus arquivos internos (`croqui.yaml`).
- **[Risco] Bibliotecas C de Terceiros quebrando por falha no `longPathAware`** →
  - **Mitigação**: O encurtamento da estrutura garante que a esmagadora maioria dos usos sequer encoste nos 260 caracteres. A dependência no manifesto é secundária (um fallback de segurança, não a única defesa).
