# Tarefas de Implementação: Tipagem Estática Estrita - Onda 4: Views e UI PySide6

## 1. Modelos Remanescentes e Views de Suporte

- [x] 1.1 Anotar com tipagem estática estrita os métodos remanescentes de `editor/models/croqui_model.py`.
- [x] 1.2 Anotar com tipagem estática estrita o módulo `editor/models/compilacao_log.py`.
- [x] 1.3 Anotar com tipagem estática estrita os módulos `editor/views/estilo.py`, `editor/views/notificacao.py`, `editor/views/publish_dialog.py`, `editor/views/tela_de_abertura.py` e `editor/views/dialogo_recuperacao_sessao.py`.


## 2. Adaptadores e Widgets de Edição

- [x] 2.1 Anotar com tipagem estática estrita `editor/views/tree_view_adapter.py` e `editor/views/protobuf_widget_factory.py`.
- [x] 2.2 Anotar com tipagem estática estrita `editor/views/widget_campo_coordenada_e7.py` e `editor/views/widget_campo_imagem.py`.
- [x] 2.3 Anotar com tipagem estática estrita `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_mapas.py`.
- [x] 2.4 Anotar com tipagem estática estrita `editor/views/widget_mensagem_coordenada.py`, `editor/views/widget_painel_referencias.py` e `editor/views/widget_saida_compilacao.py`.


## 3. Diálogos Especializados

- [x] 3.1 Anotar com tipagem estática estrita os diálogos de entidade: `dialogo_criar_pico.py`, `dialogo_criar_setor_ou_grupo.py`, `dialogo_criar_escalada.py` e `dialogo_criar_botao.py`.
- [x] 3.2 Anotar com tipagem estática estrita os diálogos de mídia e busca: `dialogo_adicionar_mapa.py`, `dialogo_busca_referencia.py`, `dialogo_inserir_imagem_markdown.py` e `dialogo_perfil_autor.py`.


## 4. Views Legadas e Entrada Principal

- [x] 4.1 Anotar com tipagem estática estrita os diálogos auxiliares: `dialogo_busca_croqui.py` e `dialogo_conexao_celular.py`.
- [x] 4.2 Anotar com tipagem estática estrita as views de edição e fluxo: `widget_editor_imagens.py` e `tela_de_carregamento.py`.
- [x] 4.3 Anotar com tipagem estática estrita a view principal `area_principal.py` e o ponto de entrada `main.py`.



## 5. Integração com Teste Guardião e Validação Global

- [x] 5.1 Atualizar `tests/tipagem_estatica_test.py` com a lista de todos os módulos da Onda 4 (`ARQUIVOS_ONDA_4`) e adicionar asserções guardiãs para as novas views e diálogos.
- [x] 5.2 Executar a suíte completa de testes (`pytest`) garantindo 100% de aprovação e integridade.
