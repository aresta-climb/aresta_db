# Proposal

## Why

Ao conectar o aplicativo móvel à prévia ao vivo de um croqui experimental no Editor Desktop, o `SyncIsolate` do aplicativo sofre uma enxurrada de erros `HTTP 404` ao baixar as imagens `.webp` na primeira tentativa, funcionando apenas eventualmente após retentativas ou recarregamento forçado. Isso ocorre por três falhas combinadas no Editor Desktop:
1. O cálculo de `id_atual` durante o salvamento lê `workspace.caminho_raiz.name` (que em croquis experimentais é um UUID opaco como `41aea39b`), fazendo com que `novo_id != id_atual` seja sempre verdadeiro e acione `renomear_pasta_croqui()` (`shutil.rmtree(compilado)`) em todo salvamento;
2. O `MonitorInatividade` (10s) dispara `salvar_croqui()` incondicionalmente mesmo quando não há edições pendentes (`isClean() == True`), apagando a pasta `compilado/` exatamente enquanto o usuário escaneia o QR Code e o celular baixa as imagens;
3. O fallback de rotas compactadas em `ClienteTunelRetransmissor` e `ServidorCelular` exige `not caminho_sub.exists()`, falhando com `HTTP 404` caso a subpasta `compilado/<id>` exista transitoriamente durante a compactação da compilação.

## What Changes

- **Resolução Fiel do ID Atual do Croqui (`workspace.py`, `area_principal.py`, `ferramentas_ciclo_vida.py`)**: Extrair e centralizar no workspace a obtenção do `id` anterior real do croqui (lendo de `database/croqui.yaml` ou `compilado/compilado.binarypb` no `ExperimentalWorkspace`, e do nome da pasta no `LocalRepoWorkspace`), garantindo que `renomear_pasta_croqui` (`shutil.rmtree(compilado)`) só seja executado quando o usuário realmente alterar o campo `id` do croqui.
- **Auto-Salvamento por Inatividade Condicionado a Modificações Pendentes (`area_principal.py`)**: Fazer com que o disparo automático do `MonitorInatividade` (10s) só execute `salvar_croqui()` quando houver alterações não salvas na pilha de histórico (`not self.historico.obter_pilha().isClean()`) ou artefatos obrigatórios ausentes, eliminando recompilações fantasmas enquanto o usuário está apenas com o diálogo de QR Code aberto conectando o celular.
- **Fallback de Rotas Compactas Sem Condição de Corrida (`tunel_retransmissor.py`, `servidor_celular.py`, `croqui_experimental.py`)**: Remover a restrição `not caminho_sub.exists()` no fallback de rotas compactas do `ClienteTunelRetransmissor._ler_arquivo_proxy` e do middleware `reescrever_rotas_compactas` do `ServidorCelular`, permitindo servir `<pasta_compilado>/<resto>` sempre que `<pasta_compilado>/<subpasta>/<resto>` não for um arquivo existente e `<pasta_compilado>/<resto>` existir como arquivo válido, além de tornar a compactação em `compilar_croqui` resiliente a diretórios preexistentes.

## Capabilities

### New Capabilities

### Modified Capabilities
- `renomeacao-croqui`: Atualiza o requisito de detecção de mudança de ID do croqui para comparar o novo ID com o ID anterior real do croqui no workspace (e não com o UUID opaco do diretório experimental), preservando a pasta `compilado/` em salvamentos normais sem renomeação.
- `editor-auto-salvamento-experimental`: Atualiza o requisito de disparo de salvamento automático por inatividade para executar apenas quando existirem modificações pendentes na pilha de histórico (`not isClean()`), evitando recompilações destrutivas durante a leitura inicial da prévia pelo celular.
- `servidor-celular`: Adiciona requisito de resolução resiliente de rotas compactadas no servidor HTTP local e no proxy do túnel WebSocket, servindo arquivos da raiz de `compilado/` independentemente da existência transitória da subpasta `<id_croqui>/`.

## Impact

- **`editor/core/workspace.py`** e **`editor/core/workspace_test.py`**: Adição de método na interface `EditorWorkspace` (`obter_id_croqui_atual()`) para retornar o ID persistido do croqui de forma determinística tanto em `ExperimentalWorkspace` quanto em `LocalRepoWorkspace`.
- **`editor/legacy_views/area_principal.py`**, **`editor/legacy_views/area_principal_test.py`** e **`editor/legacy_views/area_principal_conexao_test.py`**: Uso do ID real do croqui em `salvar_croqui()` e guarda de `isClean()` no callback de `MonitorInatividade`.
- **`editor/mcp/ferramentas_ciclo_vida.py`** e **`editor/mcp/ferramentas_ciclo_vida_test.py`**: Uso do ID real do croqui ao processar salvamento/compilação via MCP.
- **`editor/core/tunel_retransmissor.py`**, **`editor/core/tunel_retransmissor_test.py`**, **`editor/core/servidor_celular.py`** e **`editor/core/servidor_celular_test.py`**: Remoção da condição `not caminho_sub.exists()` no fallback de rotas compactadas.
- **`editor/core/croqui_experimental.py`** e **`editor/core/croqui_experimental_test.py`**: Garantia de movimentação limpa e sem colisão de artefatos na compilação incremental.
