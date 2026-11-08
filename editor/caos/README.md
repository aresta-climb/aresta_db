# Robô Caótico do Editor Aresta (`editor/caos/`)

Sistema determinístico de testes exploratórios caóticos de interface gráfica (PySide6/Qt) e *fuzz testing* de entradas para o **Editor Aresta**.

## Arquitetura e Componentes

1. **`MotorRoboCaoticoQt` (`motor_robo_caotico.py`)**:
   - Opera sobre a aplicação real do Editor com **Orçamento Ponderado**:
     - **Fase A (~10–15% dos passos)**: travessia de entrada por `TelaDeAbertura` (aviso de atualização, login OTP, `DialogoPerfilAutor`) e `TelaDeCarregamento` (`DialogoNovoCroqui`, `DialogoBuscaCroqui` e seleção de croqui do histórico).
     - **Fase B (~85–90% dos passos)**: exploração intensiva da `JanelaPrincipal` integrada (abas `Dados` com `QTreeView` e formulários `ProtobufWidgetFactory`, `Imagens`, `Mapas` com `QGraphicsScene`/sliders, `Betas`, rajadas de `Undo`/`Redo`, `Salvar`, `DialogoConexaoCelular` e `Sincronizar`).
   - Inclui o interceptador automático de diálogos modais (`vigiar_dialogos_modais()`) via `QApplication.activeModalWidget()` para desbloquear loops `.exec()` aninhados sem travar a execução.

2. **`OraculosCaos` (`oraculos_caos.py`)**:
   - **Oráculo 1 (Exceções, Logs de Erro e C++)**: intercepta `sys.excepthook`, `threading.excepthook` e qualquer log `ERROR`/`CRITICAL` no logger `aresta_editor` (incluindo exceções capturadas em `QThread` como `TarefaSalvamento` e `TarefaPublicacao`), além de validar ponteiros C++ via `shiboken6.isValid(...)`.
   - **Oráculo 2 (Simetria Determinística de `Undo`/`Redo` e Princípio VIII)**: verifica que cada índice da `QUndoStack` restaura exatamente o mesmo hash SHA-256 de `Croqui.SerializeToString(deterministic=True)` e detecta mutações silenciosas fora do histórico.
   - **Oráculo 3 (Integridade do Diário Transacional)**: valida a desserialização completa até o `EOF` de `diario_pendente.bin` e `diario_salvo.bin`.

3. **`FabricaDatasetCaos` (`fabrica_dataset_caos.py`)**:
   - Inicializa em `tmp_path` toda a estrutura de diretórios da instalação (`ARESTA_DIRETORIO_DADOS`) e um repositório Git *upstream* local real via `pygit2` (`remoto_oficial.git`, configurado por `ARESTA_GIT_UPSTREAM_URL`).
   - Gera os datasets **`normal`** e **`toxico`** (strings extremas com emojis multi-codepoint, caracteres RTL, quebras de linha, aspas YAML, coordenadas extremas, imagens PNG e betas pendentes).

4. **`BloqueadorRedeCaos` (`bloqueador_rede.py`)**:
   - Intercepta `socket.socket.connect`, `connect_ex`, `socket.create_connection` e `QDesktopServices.openUrl`, bloqueando qualquer acesso de rede externo fora de *loopback* (`127.0.0.1`, `::1`, `localhost`).

5. **`EncolhedorCaminhoCrash` (`encolhedor_caminho_crash.py`) e `ReceitaCrashRobo` (`receita_crash_robo.py`)**:
   - Reduz automaticamente sequências de falha via busca binária (*delta debugging* / `ddmin`) com poda de passos `no-op` (`mutou_estado=False`), serializa a receita mínima em JSON (`editor/caos/caminhos_regressao/`) e despacha automaticamente para o Sentry com o arquivo `.json` anexado (`capturar_crash_robo_caotico`).

6. **`executar_campanha_cli.py`**:
   - Ponto de entrada dedicado de linha de comando para rodar o *Fuzz Testing* localmente com um único comando (janela visível por padrão, envio ao Sentry com anexo `.json` habilitado e gravação em `editor/caos/caminhos_regressao/`), sem interferir nos testes unitários rápidos e *headless* do `pytest`.

## Fakes Determinísticos de Fronteira Externa

- `editor/core/cliente_auth_supabase_fake.py` (`ClienteAuthSupabaseFake`)
- `editor/core/gerenciador_sessao_fake.py` (`GerenciadorSessaoFake`)
- `editor/core/servico_submissao_fake.py` (`ServicoSubmissaoFake`)
- `editor/core/servidor_celular_fake.py` (`ServidorCelularFake`)
- `editor/plataforma/adaptador_plataforma_fake.py` (`AdaptadorPlataformaFake`)

## Como Executar

```powershell
# Executar facilmente uma campanha local de Fuzz Testing (60s, janela visível, enviando crashes + .json ao Sentry)
uv run editor/caos/executar_campanha_cli.py

# Opções da CLI local (ex: 120 segundos, modo oculto --headless ou --sem-sentry)
uv run editor/caos/executar_campanha_cli.py --duracao 120 --passos 80 --seed-inicial 5000
uv run editor/caos/executar_campanha_cli.py --headless

# Executar toda a suíte unitária e de regressão do Robô Caótico via pytest (headless)
uv run pytest editor/caos/

# Reproduzir apenas as receitas JSON salvas em editor/caos/caminhos_regressao/
uv run pytest editor/caos/regressao_caminhos_test.py
```
