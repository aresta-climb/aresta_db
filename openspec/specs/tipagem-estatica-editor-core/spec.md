# Especificação: Tipagem Estática no Editor Core

## Requirements


### Requirement: Tipagem Estática Estrita em Módulos de Fundação e Armazenamento
Os módulos de fundação (`version.py`, `formatacao.py`, `contexto.py`, `coordenadas.py`, `geometrias_poi.py`, `storage.py`) SHALL possuir anotações estritas de tipos em todas as funções, propriedades e métodos públicos e privados, sem o uso não documentado de `Any`.

#### Scenario: Validação do módulo de contexto e coordenadas pelo MyPy
- **WHEN** o MyPy analisa `editor/core/contexto.py` e `editor/core/coordenadas.py`
- **THEN** nenhuma inconsistência de tipo ou retorno `None` não tipado é reportada.

### Requirement: Tipagem Estática Estrita em Modelos de Workspace e Formato
Os módulos de workspace e serialização (`workspace.py`, `croqui_format.py`, `croqui_experimental.py`, `proto_comments.py`, `imagens_markdown.py`, `processamento_imagem_campo.py`) SHALL possuir assinaturas de tipo completas e tipagem de contratos de dados Protobuf.

#### Scenario: Validação de manipuladores de workspace pelo MyPy
- **WHEN** o MyPy analisa `editor/core/workspace.py` e `editor/core/croqui_format.py`
- **THEN** todos os argumentos de arquivo, caminho e estruturas de croqui são validados estaticamente com sucesso.

### Requirement: Tipagem Estática Estrita em Sessão, Submissão e Rede
Os módulos de gerenciamento de sessão e serviços de rede (`gerenciador_sessao.py`, `cliente_auth_supabase.py`, `servico_submissao.py`, `servico_loja.py`, `sync.py`, `worker.py`) SHALL declarar tipos estritos para payloads de autenticação, tokens, respostas de requisições e sinais PySide6.

#### Scenario: Validação de serviços de autenticação e sessão pelo MyPy
- **WHEN** o MyPy analisa `editor/core/gerenciador_sessao.py` e `editor/core/cliente_auth_supabase.py`
- **THEN** todos os tipos de retorno e estados de sessão (`SessaoUsuario | None`) são estritamente verificados.

### Requirement: Tipagem Estática Estrita em Histórico, Diário e Telemetria
Os módulos de controle de histórico, persistência binária e telemetria (`historico.py`, `diario.py`, `telemetria.py`, `registro_log.py`) SHALL possuir tipagem estrita para todos os comandos, diários de recuperação e hooks de exceção.

#### Scenario: Validação do histórico e telemetria pelo MyPy
- **WHEN** o MyPy analisa `editor/core/historico.py`, `editor/core/diario.py` e `editor/core/telemetria.py`
- **THEN** nenhuma violação de tipo é detectada e todas as chamadas de escopo e breadcrumb do Sentry são estaticamente válidas.

### Requirement: Conformidade no Teste Guardião do Repositório
O teste `tests/tipagem_estatica_test.py` SHALL incluir todos os módulos de `editor/core/` na validação contínua do Pytest, impedindo qualquer regressão de tipos no core.

#### Scenario: Execução do teste guardião com editor/core incluído
- **WHEN** a suíte de testes do Pytest é executada
- **THEN** o teste de conformidade de tipos valida `editor/core/` e passa com código 0.
