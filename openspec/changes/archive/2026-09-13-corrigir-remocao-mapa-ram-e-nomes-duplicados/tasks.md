## 1. Testes de Integração de Fronteira em Primeiro Lugar (Princípio V)

- [x] 1.1 Criar a suíte de testes de integração `editor/views/remocao_mapas_integracao_test.py` (Fase Vermelho) cobrindo o fluxo completo: adicionar mapa em setor -> verificar imagem em RAM -> remover mapa -> verificar limpeza em RAM -> re-adicionar mapa sem colisão -> desfazer remoção (imagem e mapa restaurados) -> refazer remoção.
- [x] 1.2 Adicionar cenário de teste de integração em `editor/views/remocao_mapas_integracao_test.py` cobrindo a adição de mapa em setor com nome contendo "Setor " garantindo que o nome gerado e proposto no diálogo não duplica o prefixo (Fase Vermelho).

## 2. Biblioteca Pura de Imagens do Croqui (Princípio II - Library-First & Princípio IV - TDD)

- [x] 2.1 Criar a suíte de testes unitários `editor/core/imagens_croqui_test.py` (Fase Vermelho) cobrindo `extrair_caminhos_imagens` (com Mapa, Setor, Grupo e Pico) e `obter_imagens_orfas_ao_remover` (incluindo imagens compartilhadas e imagens exclusivas).
- [x] 2.2 Implementar a biblioteca pura `editor/core/imagens_croqui.py` com as funções `extrair_caminhos_imagens` e `obter_imagens_orfas_ao_remover` até a aprovação de todos os testes unitários com 100% de cobertura (Fase Verde).

## 3. Biblioteca Pura de Nomes e Prefixos de Arquivos (Princípio II - Library-First & Princípio IV - TDD)

- [x] 3.1 Criar a suíte de testes unitários `editor/core/nomes_arquivos_test.py` (Fase Vermelho) cobrindo `deduplicar_prefixo`, `gerar_nome_mapa_sugerido` e `gerar_nome_arquivo_entidade` para diversos casos de nomes ("Setor Fugitivos I", "Fugitivos I", "Grupo Sherpa", "Sherpa", "Setor").
- [x] 3.2 Implementar a biblioteca pura `editor/core/nomes_arquivos.py` com as funções de higienização, deduplicação de prefixos e proposição de nomes até 100% de cobertura de testes unitários (Fase Verde).

## 4. Gestão de Imagens no Histórico de Exclusão (Princípio VII & Princípio IV - TDD)

- [x] 4.1 Criar testes unitários em `editor/commands/comandos_protobuf_test.py` (Fase Vermelho) cobrindo `CmdRemoverRepeated` para validar a remoção de imagens órfãs no `executar_redo()`, restauração no `undo()`, preservação de imagens compartilhadas e serialização/deserialização com imagens em RAM.
- [x] 4.2 Integrar a biblioteca `imagens_croqui.py` ao comando `CmdRemoverRepeated` em `editor/commands/comandos_protobuf.py` (Fase Verde).
- [x] 4.3 Atualizar testes no controller `editor/controllers/croqui_controller_test.py` para verificar o despacho de `remover_repeated` com limpeza de RAM (Fase Verde).

## 5. Diálogos e Visualizações da Interface (TDD)

- [x] 5.1 Atualizar `editor/views/dialogos/dialogo_adicionar_mapa_test.py` (Fase Vermelho) testando que arquivos no disco não acusam conflito de RAM e que a limpeza em RAM libera o botão de confirmação.
- [x] 5.2 Corrigir o método `_validar_estado` em `editor/views/dialogos/dialogo_adicionar_mapa.py` para usar `self.model.obter_imagens_em_memoria()` (Fase Verde).
- [x] 5.3 Atualizar `WidgetEditorDados._on_add_clicked` em `editor/views/widget_editor_dados.py` para utilizar `gerar_nome_mapa_sugerido`, com testes em `widget_editor_dados_test.py` (Fase Verde).
- [x] 5.4 Atualizar `DialogoCriarSetorOuGrupo._atualizar_proposicao_arquivo` em `editor/views/dialogos/dialogo_criar_setor_ou_grupo.py` para utilizar `gerar_nome_arquivo_entidade`, atualizando os testes em `dialogo_criar_setor_ou_grupo_test.py` (Fase Verde).

## 6. Verificação Geral e Cobertura Integral (Princípio III)

- [x] 6.1 Executar a suíte de integração `editor/views/remocao_mapas_integracao_test.py` garantindo que todos os fluxos passam (Fase Verde).
- [x] 6.2 Executar a suíte completa de testes (`pytest`) validando 100% de cobertura nos módulos novos e modificados e nenhuma regressão no repositório.
