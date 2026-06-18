## Context

A compilação de croquis atualmente ocorre de forma síncrona no editor durante a ação de salvar. Se a compilação gerar avisos ou erros, eles são apresentados numa janela `QDialog` modal. Para melhorar o fluxo, vamos substituir por um painel não-bloqueante na base da janela. 

Conforme exigido pelo arquivo `PRINCIPIOS.md`, a refatoração será feita **estritamente em Português**, adotando **TDD**, focando na **simplicidade (anti-abstração)**, e atingindo a meta inegociável de **100% de test coverage**, não os 80% solicitados anteriormente. Adotaremos também a abordagem de **Testes de Integração em Primeiro Lugar**.

## Goals / Non-Goals

**Goals:**
- Prover visualização das mensagens da compilação em um painel inferior.
- Identificar visualmente avisos e erros usando Rich Text com cores em tons pastel adequadas para temas escuros.
- Desenvolver estritamente com **TDD** (Test-Driven Development).
- Garantir a diretriz de **100% de cobertura de testes unitários** no novo código (conforme Princípio III).
- Seguir a regra de **Testes de Integração em Primeiro Lugar** (conforme Princípio V).
- Seguir a arquitetura **MVC** rigorosa existente no projeto, porém com foco em simplicidade e sem abstrações prematuras.
- Código e nomenclaturas 100% em Português Brasileiro.

**Non-Goals:**
- Edições do estado do croqui (nenhuma edição será feita a partir deste painel, logo não acionaremos a fila de `QUndoCommand` do histórico para essa rotina de visualização passiva).
- Lógica de compilação assíncrona profunda (continuaremos usando o método atual síncrono e passivo, primando pela simplicidade).

## Decisions

1. **Arquitetura MVC Simples e Clara:**
   - **Model (`models/compilacao_log.py`)**: Uma classe de dados puramente em português para armazenar o estado das mensagens de erro e aviso, emitindo sinais de mudança.
   - **Controller (`controllers/compilacao_controller.py`)**: Coordena o recebimento das saídas da compilação e decide atualizar a interface. Regra de negócio simples.
   - **View (`views/widget_saida_compilacao.py`)**: A view será um `QDockWidget` que reage passivamente ao controller. Contém o `QTextEdit` read-only com as cores em tons pastéis (ex: `#E06C75` para erro e `#E5C07B` para aviso).

2. **Testes e Integração Primeiro:**
   - **Testes de Integração**: Antes dos testes unitários profundos das classes, criaremos um teste de integração conectando a chamada do Controller à atualização visual e comportamental do Model, definindo as fronteiras claramente.
   - **TDD Rigoroso**: Todos os novos arquivos (e.g. `compilacao_controller.py`) terão seu par `_test.py` (e.g. `compilacao_controller_test.py`) implementados **antes** da lógica de produção.

3. **Integração com `JanelaPrincipal` (`legacy_views/area_principal.py`):**
   - O `CompilacaoController` será instanciado no ciclo de vida principal.
   - O widget de interface proveniente da View será ancorado na `BottomDockWidgetArea`.
   - O acoplamento antigo com o `DialogoErrosCompilacao` será removido, mas mantendo a simplicidade do fluxo legado de save para evitar complexidades adicionais não requisitadas.
