## Context

O Editor Aresta possui um fluxo de salvamento acionado pelo botão "Salvar" na barra superior da interface:
1. `area_principal.py` aciona a `TarefaSalvamento` em linha de execução secundária (`worker.py`).
2. `CroquiModel.extrair_arquivos_e_serializar` serializa o estado em memória para os arquivos `croqui.yaml` e arquivos `.md` externos no diretório `database/`.
3. `workspace.processar_renomeacao_e_compilacao` executa a função `deploy()` de `scripts/deploy_generated.py`.
4. `deploy()` chama `compilar_croqui()` de `scripts/preparar_submissao_lib.py`, expandindo arquivos markdown e gerando `compilado.yaml` e `compilado.binarypb`.
5. `deploy()` chama `gerar_compilado_md()` de `scripts/gerar_compilado_md.py` para produzir o arquivo de depuração `compilado.md`.

Nesse fluxo, foram identificadas três fragilidades interdependentes:
- **Heurística de tipo de contêiner**: `expandir_arquivo_generico` avaliava `filhos = frontmatter.get("setores")` e, caso a lista estivesse vazia, tratava o arquivo como `setor`, criando discrepância entre o que o `croqui.yaml` declarou como `grupo` e o que foi gerado no `compilado.yaml`.
- **Ausência de tratamento seguro contra nulos no gerador markdown**: `gerar_compilado_md.py` esperava correspondência exata de tipos e chamava `.get()` em `dados_compilados` mesmo quando nulo, disparando `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Perda de rastreamento e mensagem crua**: `deploy_generated.py` capturava a exceção, convertia para texto sem `traceback.format_exc()` e lançava um novo `RuntimeError` desvinculado (`without from e`). A interface gráfica apresentava essa mensagem técnica bruta em um diálogo crítico simples.

## Goals / Non-Goals

**Goals:**
- Permitir a compilação completa e sem falhas de croquis contendo Picos vazios, Grupos sem setores e Setores sem vias.
- Corrigir a identificação de tipo em `preparar_submissao_lib.py` para respeitar referências de `grupo` mesmo com lista `setores: []`.
- Garantir tratamento seguro contra nulos em `gerar_compilado_md.py`, suportando estruturas incompletas ou nulas sem estourar exceções.
- Preservar a causa raiz e o rastreamento completo de exceções no pipeline de deploy (`raise RuntimeError(...) from e` e registro de logs).
- Implementar biblioteca dedicada `dialogo_erro_salvamento.py` (Library-First) para apresentação de diálogo amigável, acolhedor e informativo na interface com seção técnica expansível ("Mostrar Detalhes") e botão de cópia rápida.
- Garantir 100% de cobertura de testes unitários para todas as alterações e novas bibliotecas.
- Adotar Testes de Integração em Primeiro Lugar antes dos testes unitários aprofundados.

**Non-Goals:**
- Não permitir que salvamentos que falhem por outros erros críticos continuem silenciosamente: a integridade do banco de dados local continua garantida pela interrupção do salvamento em caso de erro real.
- Não alterar os esquemas de Protobuf nem quebrar compatibilidade com croquis existentes.

## Decisions

### Decisão 1: Identificação Confiável de Grupos Vazios em `preparar_submissao_lib.py`
- **Abordagem**: Em `expandir_arquivo_generico(obj_ref, pico_path, tipo_esperado=None)`, aceitar o tipo explicitamente informado pelo chamador (`"grupo"` ou `"setor"` de acordo com a chave no `croqui.yaml`). Além disso, verificar se a chave `"setores"` existe no frontmatter (`"setores" in frontmatter`), tratando listas vazias `[]` como grupos válidos.
- **Alternativas consideradas**:
  - *Manter a heurística apenas por tamanho*: descartado, pois inviabiliza criar um grupo antes de criar seus setores.
  - *Criar um arquivo temporário com setores fictícios*: descartado por violar o princípio de simplicidade e poluir o repositório.

### Decisão 2: Defensividade e Tolerância a Nulos em `gerar_compilado_md.py`
- **Abordagem**: Tratar `dados_compilados` e `conteudo` como opcionais. Se `dados_compilados` for `None` ou não for um dicionário, preencher com `{}`. Se um grupo não contiver setores (`filhos_originais` ou `filhos_compilados` vazios), não iterar sobre setores inexistentes e renderizar a seção correspondente como vazia.
- **Alternativas consideradas**:
  - *Silenciar a geração de compilado.md em caso de erro*: descartado, pois queremos que o compilado.md funcione e reflita o estado real do croqui.

### Decisão 3: Encadeamento Explícito de Exceções (`raise ... from e`) em `deploy_generated.py`
- **Abordagem**: No bloco `except Exception as e:` da compilação de cada croqui:
  1. Registrar `traceback.format_exc()` na saída do console para visibilidade no painel do editor.
  2. Reter a tupla `(croqui_id, e, traceback_str)`.
  3. No ponto de lançamento de erro final, usar `raise RuntimeError(...) from e` (ou encadear o primeiro erro capturado).
- **Impacto**: O Sentry detecta automaticamente a `__cause__` da exceção e desenha a árvore de rastreamento até a linha de código exata da falha.

### Decisão 4: Biblioteca Dedicada para Diálogo de Erro (Library-First)
- **Abordagem**: Criar o módulo independente `editor/views/dialogo_erro_salvamento.py` contendo a função `exibir_dialogo_erro_salvamento(pai, erro, traceback_detalhado)`:
  1. Título: `"Não foi possível salvar o croqui"`.
  2. Texto Principal (`setText`): Informa que ocorreu um erro durante a compilação e tranquiliza o usuário de que seus dados em tela permanecem preservados.
  3. Detalhes (`setDetailedText`): Contém a mensagem de erro detalhada e o rastreamento capturado sanitizado.
  4. Botão "Copiar Detalhes": Botão que copia o texto completo para o `QClipboard`.
  5. A classe `AreaPrincipal` delega completamente a exibição para essa biblioteca, mantendo o acoplamento mínimo.
- **Alternativas consideradas**:
  - *Embutir lógica diretamente no método de AreaPrincipal*: descartado por violar o Princípio II (Library-First).
  - *Criar uma janela modal inteiramente personalizada (QDialog do zero)*: descartado pelo princípio da simplicidade (Princípio VI); o `QMessageBox` do Qt já oferece `setDetailedText` nativo e com suporte a acessibilidade e layout padronizado do sistema operacional.

## Alinhamento aos Princípios de Engenharia (`PRINCIPIOS.md`)

1. **Tudo em Português**: Toda a documentação, nomes de arquivos, funções, variáveis e mensagens da interface são estritamente em português brasileiro.
2. **Library-First**: A funcionalidade de apresentação de erro é construída como uma biblioteca independente (`dialogo_erro_salvamento.py`), com testes próprios e sem acoplamento à janela principal.
3. **100% de Cobertura de Testes Unitários**: Todo código novo ou modificado possui testes unitários que garantem 100% de cobertura.
4. **TDD (Test-Driven Development)**: Cada tarefa segue estritamente o ciclo Vermelho-Verde-Refatorar.
5. **Testes de Integração em Primeiro Lugar**: O contrato ponta a ponta (salvamento e compilação de croqui com estruturas vazias) é estabelecido na primeira fase, antes dos testes unitários profundos.
6. **Simplicidade e Anti-Abstração**: Uso direto do `QMessageBox` com `setDetailedText`, sem camadas desnecessárias de abstração.

## Risks / Trade-offs

- **[Risco] Pré-computados com grupos e picos zerados no aplicativo móvel** → *Mitigação*: O aplicativo Aresta Mobile e o Protobuf já lidam normalmente com contadores zerados (`total_escaladas: 0`, `total_setores: 0`).
- **[Risco] Compatibilidade do formato de rastreamento no QMessageBox** → *Mitigação*: Sanitizar texto e caminhos locais usando `sanitizar_texto_caminhos` antes de exibir no diálogo de detalhes, respeitando a privacidade do usuário.
