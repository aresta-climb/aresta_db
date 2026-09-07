## Why

Durante a edição de um croqui no Editor Aresta, salvar o trabalho em progresso é um hábito frequente e natural. No entanto, ao criar um novo Pico ou Grupo que ainda não possui setores ou vias cadastrados, o processo de salvamento falhava criticamente com `AttributeError: 'NoneType' object has no attribute 'get'` na geração de arquivos de depuração (`gerar_compilado_md.py`) e na heurística de expansão de grupos vazios (`preparar_submissao_lib.py`). 

Além disso, a falha era apresentada ao usuário através de uma caixa de diálogo genérica com mensagens técnicas confusas, enquanto o Sentry e os logs perdiam o rastreamento original da exceção devido a um encapsulamento inadequado em `deploy_generated.py`.

Esta mudança resolve a causa raiz tornando o compilador resiliente a estruturas vazias ou em progresso, preserva o rastreamento completo de exceções para telemetria/logs e melhora a experiência do usuário com um diálogo de erro claro e detalhável através de uma biblioteca isolada, seguindo integralmente todos os princípios definidos em `PRINCIPIOS.md`.

## What Changes

- **Suporte a Picos, Grupos e Setores Vazios**: O pipeline de compilação (`scripts/preparar_submissao_lib.py` e `scripts/gerar_compilado_md.py`) passa a suportar nativamente estruturas que ainda não possuem setores, vias ou propriedades preenchidas, eliminando suposições de não-nulidade e a heurística que rebaixava grupos vazios para setores.
- **Preservação de Rastreamento de Exceções**: Em `scripts/deploy_generated.py`, as exceções capturadas durante a compilação passam a ser encadeadas explicitamente (`raise RuntimeError(...) from e`) e o rastreamento completo é impresso no console de saída de compilação, permitindo que o Sentry e desenvolvedores identifiquem a linha exata de falhas.
- **Biblioteca Dedicada para Diálogo de Erro de Salvamento (Library-First)**: Criação da biblioteca `editor/views/dialogo_erro_salvamento.py` com testes unitários em `editor/views/dialogo_erro_salvamento_test.py`, isolando a formatação e apresentação do diálogo estruturado de erro com mensagem limpa, detalhes técnicos expansíveis ("Mostrar Detalhes") e botão de cópia rápida.
- **Integração na Janela Principal**: Em `editor/legacy_views/area_principal.py`, delegação da exibição de falhas na persistência/compilação para a nova biblioteca `dialogo_erro_salvamento`.

## Capabilities

### New Capabilities
- `compilacao-estruturas-vazias`: Suporte à compilação, cálculo de pré-computados e geração de documentação markdown para croquis contendo picos, grupos e setores vazios ou sem filhos cadastrados.

### Modified Capabilities
- `editor-area-principal`: Aprimoramento do tratamento e apresentação de falhas de salvamento com diálogo estruturado, mensagem orientativa e detalhes técnicos expansíveis fornecidos pela biblioteca `dialogo_erro_salvamento`.
- `compilation-output-panel`: Preservação e exibição de rastreamentos completos formatados quando ocorrem exceções na rotina de compilação disparada pelo salvamento.

## Impact

- `scripts/preparar_submissao_lib.py`: Ajuste em `expandir_arquivo_generico` para respeitar o tipo declarado (`grupo`) mesmo quando a lista de setores estiver vazia.
- `scripts/gerar_compilado_md.py`: Proteção contra valores nulos em `dados_compilados`, `conteudo` e iterações de listas vazias.
- `scripts/deploy_generated.py`: Encadeamento de exceções com `from e` e registro de rastreamento completo no console.
- `editor/views/dialogo_erro_salvamento.py` [NOVO]: Nova biblioteca de interface para exibição estruturada e cópia de detalhes de erro ao salvar.
- `editor/views/dialogo_erro_salvamento_test.py` [NOVO]: Testes unitários com 100% de cobertura para a nova biblioteca.
- `editor/core/worker.py` e `editor/legacy_views/area_principal.py`: Trânsito estruturado de erro (mensagem amigável + rastreamento técnico) e delegação para o novo diálogo.
