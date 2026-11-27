# editor-headless-mode Specification

## Purpose

Define o terceiro modo oficial de entrada do Editor Aresta (`Modo Headless`), permitindo carregar, inspecionar, editar, compilar e salvar croquis em `database/<id>` via ferramentas MCP sem instanciar janelas gráficas, isolando a saída compilada em diretório temporário descartável.

## Requirements

### Requirement: Terceira Porta Oficial de Entrada do Editor em Modo Headless
O Editor Aresta SHALL oferecer um modo oficial *headless* acessível tanto por API programática quanto pela linha de comando (`--headless <caminho_croqui>`), inicializando o ambiente Qt em modo `offscreen` sem instanciar janelas, diálogos de login ou `QWidget`s visuais.

#### Scenario: Inicialização programática de sessão headless sobre croqui oficial
- **WHEN** um consumidor interno (como o agente de resolução de feedbacks) abre uma sessão *headless* apontando para `database/<croqui_id>`
- **THEN** o Editor aplica eventuais migrações pendentes, carrega `croqui.yaml` e seus arquivos externos no modelo de domínio com histórico de comandos ativo e disponibiliza o catálogo de ferramentas MCP para chamadas diretas em memória

#### Scenario: Inicialização via linha de comando com flag --headless
- **WHEN** o Editor é executado via CLI com `--headless database/<croqui_id>`
- **THEN** o processo inicia sem abrir `TelaDeAbertura`, `TelaDeCarregamento` ou `JanelaPrincipal` e atende requisições JSON-RPC 2.0 do protocolo MCP para o croqui carregado

### Requirement: Compilação Real Isolada em Diretório Temporário no Workspace Headless
Ao executar `aresta_compilar` ou `aresta_salvar` no modo *headless*, o workspace SHALL persistir os arquivos-fonte canônicos em `database/<croqui_id>` e executar o pipeline completo de compilação em um diretório temporário isolado, sem criar ou modificar arquivos em `generated/` nem `STATUS_CROQUIS.md`.

#### Scenario: Salvamento e compilação limpa sem sujar artefatos fora de database/<croqui_id>
- **WHEN** um agente realiza edições (como alterar campos, criar um novo setor e migrar uma escalada) na sessão *headless* e invoca `aresta_salvar`
- **THEN** o Editor grava `croqui.yaml` e os arquivos `.md` correspondentes (incluindo cabeçalhos SPDX `ODbL-1.0` em novos setores) dentro de `database/<croqui_id>/`, valida a compilação completa em diretório temporário e mantém `generated/` e `STATUS_CROQUIS.md` inalterados

#### Scenario: Propagação de erros de compilação no modo headless
- **WHEN** o estado em memória do croqui contém uma violação de integridade detectada pelo compilador e o agente invoca `aresta_compilar` ou `aresta_salvar`
- **THEN** a ferramenta retorna as mensagens de erro ou aviso geradas pelo compilador para que o agente possa corrigir o estado antes de encerrar a sessão
