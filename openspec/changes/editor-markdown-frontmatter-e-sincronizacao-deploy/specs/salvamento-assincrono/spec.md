## ADDED Requirements

### Requirement: Recarregamento Condicional da Interface pós-salvamento
O sistema SHALL detectar quando rotinas automáticas de compilação ou migração alteram arquivos no diretório `database/` durante o salvamento e recarregar os dados na interface apenas quando tais modificações ocorrerem.
- **Detecção de Alteração no Database**: O pipeline de compilação (`deploy_generated.py` / `corrigir_database`) SHALL sinalizar se algum arquivo de entrada dentro de `database/` foi criado, movido, alterado ou excluído.
- **Propagação do Estado**: A thread de salvamento em background (`TarefaSalvamento`) SHALL transmitir a indicação de alteração no database junto ao sinal de conclusão de salvamento.
- **Recarregamento Sob Demanda**: Ao receber a confirmação de que o database foi alterado pelo compilador, o editor SHALL recarregar o modelo de dados a partir do disco e atualizar os componentes visuais.
- **Preservação de Foco e Seleção**: Durante o recarregamento condicional, o editor SHALL preservar a seleção do item ativo na árvore de navegação e o formulário em exibição.
- **Sem Recarga Desnecessária**: Quando nenhuma alteração tiver ocorrido nos arquivos de `database/`, o editor SHALL manter o estado da interface inalterado, sem executar leituras extras do disco.

#### Scenario: Salvamento sem modificações no database
- **WHEN** o usuário salva um croqui cujos arquivos no `database/` não sofrem alterações automáticas pelo compilador
- **THEN** a rotina de salvamento conclui sem disparar recarregamento de disco ou reconstrução da interface.

#### Scenario: Salvamento com migração de imagens no database
- **WHEN** o compilador move imagens de `raw_pdf_contents` para `imagens/` e atualiza referências nos arquivos do `database/`
- **THEN** o editor detecta a alteração, recarrega o modelo de dados do disco, atualiza os campos na tela e mantém o nó da árvore selecionado pelo usuário.
