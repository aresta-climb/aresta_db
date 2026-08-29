# Tarefas de Implementacao: Tipagem Estatica Estrita - Onda 5

## 1. Ferramentas de Release e Proxies

- [x] 1.1 Anotar com tipagem estatica estrita editor/models/readonly_proxy.py.
- [x] 1.2 Anotar com tipagem estatica estrita editor/release_tools/bump_version.py e editor/release_tools/calculate_next_dev.py.


## 2. Pipeline de Migracoes de Banco de Dados

- [x] 2.1 Anotar com tipagem estatica estrita os modulos em migracoes/ (0001_migrar_secoes_para_botoes.py, 0002_centralizar_map_references.py, 0003_migrar_mapas_gerais.py, 0004_padronizar_geometrias_poi.py e append.py).
- [x] 2.2 Anotar com tipagem estatica estrita scripts/helpers_migracao.py, scripts/migrador.py, scripts/migrar_banco.py e scripts/migrar_publicar_croqui.py.


## 3. Scripts de Processamento, Compilacao e Imagens

- [x] 3.1 Anotar com tipagem estatica estrita os scripts de imagem e OCR: comprimir_imagens.py, editar_imagens.py, extrair_ocr_lote.py, renomear_imagens.py, repartir_pdf.py e visualizar_mapa_processado.py.
- [x] 3.2 Anotar com tipagem estatica estrita os scripts de compilacao e exportacao: deploy_generated.py, exportar_para_anchor_ledge.py, finalizar_mapas.py, gerar_compilado_md.py, gerar_croqui_experimental.py e gerar_mapping_json.py.

- [x] 3.3 Anotar com tipagem estatica estrita os scripts de auditoria e validacao: medir_saude_croquis.py, preparar_extracao_de_mapas.py, preparar_submissao_lib.py, recalcular_coordenadas.py, validador_cabecalhos.py, verificar_binarypb.py, visualizar_uso_protobuf.py, visualizar_uso_protobuf_lib.py e add_options.py.


## 4. Serving e Validacao de PRs

- [x] 4.1 Anotar com tipagem estatica estrita serving/pr_db_validator.py e serving/update_serving.py.


## 5. Integracao com Teste Guardiao e Validacao Global

- [x] 5.1 Atualizar tests/tipagem_estatica_test.py com a lista ARQUIVOS_ONDA_5 para validacao MyPy e metateste AST.
- [x] 5.2 Executar a suite completa de testes (pytest) garantindo 100% de aprovacao e integridade.

