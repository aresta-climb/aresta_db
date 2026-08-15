## Why

O aplicativo foi rejeitado na Microsoft Store com o erro `WinError 206` (MAX_PATH) durante a compilação do setup de croquis experimentais. A virtualização do Windows (`LocalCache\Roaming`) infla o caminho base de dados da aplicação, o que em combinação com a estrutura redundante de pastas (`EditorAresta/aresta_editor`) e o nome longo de projeto baseado no título da montanha, acaba estourando o limite histórico de 260 caracteres do Windows.

## What Changes

- **Simplificação de Estrutura de Pastas**: A pasta base `EditorAresta/aresta_editor` será simplificada para usar apenas `EditorAresta`.
- **Encurtamento de Nomes de Pastas**: A pasta raiz dos croquis experimentais (hoje `croquis_experimentais`) será renomeada para `croquis`.
- **Identificadores Aleatórios**: Em vez de pastas com `[timestamp]_[nome_da_montanha]`, o sistema passará a gerar pastas nomeadas com um ID curto aleatório de 8 dígitos alfanuméricos.
- **Manifesto do MSIX**: Adição da diretiva `longPathAware` ao `AppxManifest.xml` para indicar ao SO que o aplicativo lida com caminhos grandes.
- **Clonagem Git Segura**: O uso monolítico de `pygit2.clone_repository` será desconstruído. Passaremos a usar `init_repository`, configurando manualmente `core.longpaths = True` antes de executar qualquer `fetch` e `checkout`. Isso garantirá a tolerância do motor C do Git a caminhos longos antes da extração de arquivos.
- **Melhorias de UI no Histórico**: Como o nome físico da pasta será um ID opaco (ex: `9aecd32d`), a tela de histórico mostrará este ID visivelmente para facilitar a busca no Explorador de Arquivos, e a lista de croquis será ordenada pela data de edição do `croqui.yaml` (visto que a ordem alfabética das pastas não fará mais sentido cronológico).
- **Aderência aos Princípios (PRINCIPIOS.md)**: A implementação seguirá estritamente o ciclo TDD (Test-Driven Development) e manterá 100% de test coverage para qualquer alteração, garantindo que as lógicas de leitura/escrita não quebrem e que tudo seja implementado em português do Brasil.

## Capabilities

### New Capabilities
- `windows-long-path-support`: Define a habilitação formal do suporte ao limite estendido de caminhos no ecossistema do Windows.

### Modified Capabilities
- `editor-arquitetura`: Muda os requisitos de armazenamento de dados e geração das pastas dos croquis.
- `editor-sincronizacao-git`: Especifica que o processo de clonagem agora DEVE garantir o `core.longpaths` localmente antes de iniciar a extração.

## Impact

- `editor/core/storage.py` (paths base)
- `editor/core/croqui_experimental.py` (gera nomes de pastas e pygit2 clone)
- `editor/core/sync.py` (pygit2 clone)
- `editor/msix/AppxManifest.xml` (manifesto MSIX)
