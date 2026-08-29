# Design Tecnico: Tipagem Estatica Estrita - Onda 5

## Arquitetura e Estrategia de Tipagem

A Onda 5 abrange os utilitarios de automacao, processamento de dados e deploy do repositorio:

### Grupo 1: Ferramentas de Release e Proxies
- editor/models/readonly_proxy.py: Tipagem com TypeVar e protocolos para encapsulamento seguro de leitura de mensagens Protobuf.
- editor/release_tools/bump_version.py e editor/release_tools/calculate_next_dev.py: Tipagem de versoes semanticas, manipulacao de arquivos e CLI.

### Grupo 2: Pipeline de Migracoes de Banco de Dados
- migracoes/ (0001, 0002, 0003, 0004, append.py) e scripts/ (helpers_migracao.py, migrador.py, migrar_banco.py, migrar_publicar_croqui.py).

### Grupo 3: Scripts de Automacao, Imagens e Compilacao
- Scripts de imagem e OCR (comprimir_imagens.py, editar_imagens.py, extrair_ocr_lote.py, renomear_imagens.py, repartir_pdf.py, visualizar_mapa_processado.py).
- Scripts de compilacao e exportacao (deploy_generated.py, exportar_para_anchor_ledge.py, finalizar_mapas.py, gerar_compilado_md.py, gerar_croqui_experimental.py, gerar_mapping_json.py).
- Scripts de auditoria e validacao (medir_saude_croquis.py, preparar_extracao_de_mapas.py, preparar_submissao_lib.py, recalcular_coordenadas.py, validador_cabecalhos.py, verificar_binarypb.py, visualizar_uso_protobuf.py, visualizar_uso_protobuf_lib.py, add_options.py).

### Grupo 4: Serving e Validacao de PRs
- serving/pr_db_validator.py e serving/update_serving.py.

### Grupo 5: Testes Guardioes
- tests/tipagem_estatica_test.py com ARQUIVOS_ONDA_5.
