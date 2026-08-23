## 1. Infraestrutura de Shadow State e Sincronização Reativa (TDD)

- [x] 1.1 Atualizar `editor/models/croqui_model_test.py` (Red) para cobrir o sinal `imagem_alterada` e operações de consulta/atualização em RAM `_imagens_em_memoria`.
- [x] 1.2 Implementar sinal `imagem_alterada` e aprimorar métodos de imagem em RAM em `editor/models/croqui_model.py` (Green).
- [x] 1.3 Criar testes unitários para comandos `QUndoCommand` de imagem (`CmdSubstituirImagemMemoria`, `CmdAdicionarMapaMemoria`, `CmdRemoverMapaMemoria`) em `editor/controllers/croqui_controller_test.py` (Red).
- [x] 1.4 Implementar comandos `QUndoCommand` para imagens e mapas em RAM em `editor/controllers/croqui_controller.py` (Green).

## 2. Diálogo Robusto de Adicionar Mapa (TDD)

- [x] 2.1 Criar a suíte de testes unitários `editor/views/dialogos/dialogo_adicionar_mapa_test.py` (Red) cobrindo seleção por botão, drag & drop, extração e exibição de metadados ricos (dimensões, tamanho formatado e formato), pré-processamento automático para WebP e validação reativa de nomes e colisões com a RAM e a pasta `imagens/`.
- [x] 2.2 Implementar a nova interface e lógica do `DialogoAdicionarMapa` em `editor/views/dialogos/dialogo_adicionar_mapa.py` utilizando as funções puras de `editor/core/processamento_imagem_campo.py` e operando em RAM (Green).

## 3. Substituição de Imagem e Navegação no Editor de Mapas (TDD)

- [x] 3.1 Criar a suíte de testes unitários `editor/views/widget_editor_mapas_imagem_test.py` (Red) cobrindo a ação de substituição de imagem de fundo do mapa com pré-processamento WebP e comando `QUndoCommand` em RAM, a ação de focar a imagem do mapa no Editor de Imagens, e a sincronização reativa ao sinal `imagem_alterada`.
- [x] 3.2 Implementar os botões e ações "Substituir Imagem..." e "Abrir no Editor de Imagens" na barra de ferramentas e a assinatura de `imagem_alterada` em `editor/views/widget_editor_mapas.py` (Green).

## 4. Substituição de Imagem no Editor de Imagens (TDD)

- [x] 4.1 Criar a suíte de testes unitários `editor/legacy_views/widget_editor_imagens_substituicao_test.py` (Red) cobrindo o botão "Substituir Imagem...", pré-processamento WebP em RAM via `QUndoCommand`, sincronização com `imagem_alterada` e atualização da lista e cena gráfica.
- [x] 4.2 Implementar o botão "Substituir Imagem..." e a sincronização reativa em `editor/legacy_views/widget_editor_imagens.py` (Green).

## 5. Testes de Integração de Fronteira e Sincronização entre Abas

- [x] 5.1 Criar a suíte de testes de integração `editor/legacy_views/mapas_imagens_integracao_test.py` verificando a adição de mapas com novo diálogo em RAM, substituição de imagem preservando POIs, sincronização mútua entre mapas e imagens sem escrita em disco antes de salvar, e suporte a Undo/Redo global.

## 6. Validação Geral e Cobertura

- [x] 6.1 Executar a suíte completa de testes (`pytest`) certificando 100% de cobertura nos módulos novos/modificados e nenhuma regressão no repositório.
- [x] 6.2 Validar a compilação do banco de dados com `deploy_generated.py`.
