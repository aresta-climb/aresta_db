# Design

## Context

Veja `proposal.md` para a motivação e a análise das três causas raiz dos erros `HTTP 404` iniciais ao conectar o celular à prévia ao vivo.
Atualmente:
- Em `editor/core/croqui_experimental.py`, `_criar_estrutura_croqui` cria diretórios experimentais usando um identificador curto opaco (`uuid.uuid4().hex[:8]`, ex: `41aea39b`) para economizar caracteres de caminho no Windows (`MAX_PATH`), e `compilar_croqui` compacta os artefatos compilados movendo `compilado/<id_croqui>/*` diretamente para `compilado/`.
- Em `editor/legacy_views/area_principal.py` (linhas 1082–1085) e `editor/mcp/ferramentas_ciclo_vida.py` (linhas 63–65), o cálculo de `id_atual` ainda assume o formato legado `<timestamp>_<id_croqui>` em `workspace.caminho_raiz.name`. Como `caminho_raiz.name` é um UUID opaco no `ExperimentalWorkspace`, `novo_id != id_atual` resulta sempre em `True`, acionando `renomear_pasta_croqui()` (`shutil.rmtree(compilado)`) em todo salvamento.
- Em `editor/legacy_views/area_principal.py` (linhas 1682–1688), `_abrir_dialogo_conexao_celular` conecta `MonitorInatividade.inatividade_detectada` (10s) diretamente a `self.salvar_croqui`, que executa `TarefaSalvamento` mesmo quando `self.historico.obter_pilha().isClean()` é `True`.
- Em `editor/core/tunel_retransmissor.py` (`_ler_arquivo_proxy`) e `editor/core/servidor_celular.py` (`reescrever_rotas_compactas`), o fallback de `<id_croqui>/<resto>` para `<resto>` exige `not caminho_sub.exists()`.

## Goals / Non-Goals

**Goals:**
- Eliminar 100% das exclusões acidentais da pasta `compilado/` em salvamentos onde o `id` do croqui não mudou.
- Impedir que o `MonitorInatividade` dispare recompilações em segundo plano quando não houver modificações pendentes (`isClean() == True`).
- Tornar a resolução de arquivos estáticos/binários em `ServidorCelular` e `ClienteTunelRetransmissor` imune à presença transitória da subpasta `<id_croqui>/` durante ou após a compilação.
- Seguir estritamente os 8 princípios do `AGENTS.md`: código e identificadores 100% em português brasileiro, arquitetura Library-First, TDD (Red-Green-Refactor), 100% de cobertura comportamental nos módulos tocados e zero mocks para código interno nos novos testes (e refatoração de mocks legados nos trechos tocados conforme Regra do Escoteiro).

**Non-Goals:**
- Alterar o protocolo do Cloudflare Worker (`previa.arestaclimb.com`) ou do aplicativo Flutter (`aresta_app`), pois o contrato de rede atual já funciona perfeitamente assim que o Editor Desktop deixa de apagar `compilado/` durante o download.
- Alterar a estrutura de pastas UUID opacas do `ExperimentalWorkspace` (que é necessária para suporte a caminhos longos no Windows).

## Decisions

### 1. Método `obter_id_croqui_atual()` no Contrato `EditorWorkspace` (`editor/core/workspace.py`)
- **Decisão**: Adicionar o método `obter_id_croqui_atual() -> str` ao protocolo `EditorWorkspace` e às implementações `ExperimentalWorkspace` e `LocalRepoWorkspace`:
  - Em `LocalRepoWorkspace`: retorna `self.caminho_raiz.name` (pois no modo repositório local a pasta raiz é literalmente `database/<id_croqui>`).
  - Em `ExperimentalWorkspace`: lê o `id` persistido anteriormente em `compilado/compilado.binarypb` (via `croqui_pb2.Croqui.FromString`) ou, caso ainda não exista binário compilado, do arquivo `database/croqui.yaml` no disco; apenas se nenhum dos dois existir ou contiver `id`, faz fallback para o `id_original` em `croqui_experimental.yaml` ou para `self.caminho_raiz.name`.
  - Tanto `area_principal.py` quanto `ferramentas_ciclo_vida.py` (e o próprio `ExperimentalWorkspace.processar_renomeacao_e_compilacao` quando `id_atual` coincidir com `caminho_raiz.name`) utilizarão `workspace.obter_id_croqui_atual()` para determinar se houve de fato mudança de ID.
- **Racional**: Centraliza a responsabilidade de descobrir o ID persistido na abstração correta (`EditorWorkspace`), eliminando a duplicação da lógica legada de `split("_", 1)` na UI e no servidor MCP.
- **Alternativas consideradas**:
  - *Guardar `self._id_original_carregado` apenas na `AreaPrincipal`*: Não cobriria chamadas diretas a `ExperimentalWorkspace.processar_renomeacao_e_compilacao` ou ao MCP quando o nome da pasta é repassado. Colocar no `Workspace` protege todas as fronteiras.

### 2. Guarda de Modificações Pendentes no Auto-Salvamento por Inatividade (`editor/legacy_views/area_principal.py`)
- **Decisão**: Conectar `self.monitor_inatividade.inatividade_detectada` a um método dedicado `_ao_detectar_inatividade_celular()` em `AreaPrincipal`, que verifica se há modificações não salvas (`not self.historico.obter_pilha().isClean()`) ou se faltam os artefatos de índice (`indice.binarypb` / `catalogo.db`) antes de invocar `self.salvar_croqui()`.
- **Racional**: O salvamento manual (`Ctrl+S` ou botão Salvar) continua permitindo que o usuário force o salvamento/compilação quando desejar, enquanto o disparo automático silencioso a cada 10s de inatividade só roda quando o usuário efetivamente editou algo e parou de interagir.

### 3. Fallback Direto de Rota Compactada sem Restrição `not caminho_sub.exists()` (`tunel_retransmissor.py` e `servidor_celular.py`)
- **Decisão**: Em `ClienteTunelRetransmissor._ler_arquivo_proxy` e no middleware `reescrever_rotas_compactas` de `ServidorCelular`, quando `caminho_alvo` (`<pasta_compilado>/<subpasta>/<resto>`) não for um arquivo existente (`not caminho_alvo.is_file()`), verificar apenas se `caminho_direto` (`<pasta_compilado>/<resto>`) está contido em `pasta_compilado` e é um arquivo existente (`caminho_direto.is_file()`), removendo a exigência `and not caminho_sub.exists()`. Adicionalmente, em `GerenciadorCroquiExperimental.compilar_croqui`, ao mover subitens de `pasta_previa` / `pasta_croqui` para o destino, remover previamente qualquer destino conflitante (`shutil.rmtree` para diretório ou `unlink` para arquivo) para evitar que `shutil.move` aninhe `imagens/imagens` caso uma pasta anterior tenha restado no destino.
- **Racional**: Se o arquivo específico solicitado já não foi encontrado em `<pasta_compilado>/<subpasta>/<resto>`, a existência de um diretório vazio ou parcial `<pasta_compilado>/<subpasta>` nunca deve impedir a entrega do arquivo válido presente em `<pasta_compilado>/<resto>`.

## Risks / Trade-offs

- **[Risco] Leitura de `compilado.binarypb` ou `croqui.yaml` em `obter_id_croqui_atual()` antes de `persistir_contexto_memoria_no_disco`** → *Mitigação*: Como `salvar_croqui()` extrai os dados em memória (`persistir_no_disco=False`) antes de instanciar `TarefaSalvamento`, o arquivo `database/croqui.yaml` e o `compilado/compilado.binarypb` no disco ainda contêm exatamente o ID anterior à edição em memória, tornando a leitura em disco antes da persistência uma fonte 100% confiável do ID anterior.
