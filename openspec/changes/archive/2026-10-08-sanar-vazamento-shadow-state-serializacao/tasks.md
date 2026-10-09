# Tasks: Sanar Vazamento de Shadow State na Serialização do Editor

## 1. Testes de Integração e Contrato de Serialização (Red)

- [x] 1.1 Criar testes de contrato em `tests/contrato_editor_serializacao_test.py` reproduzindo o salvamento de croquis onde `mapas_gerais`, `setor`, `grupo`, `secao_textual` e `Croqui` possuem extensões de shadow state (`ext_metadados_arquivo`) sem `conteudo` inline, verificando que falham inicialmente com `ValueError` ao validar com `validar_sem_extensoes_vazadas`

## 2. Biblioteca Pura de Sanitização de Dicionários (TDD)

- [x] 2.1 Criar testes unitários em `editor/core/serializacao_util_test.py` para a função pura `sanitizar_dicionario_sem_extensoes`, validando a remoção de chaves iniciadas por `[` ou contendo `ext_metadados` em estruturas com listas e dicionários aninhados, garantindo preservação de campos canônicos
- [x] 2.2 Implementar a função `sanitizar_dicionario_sem_extensoes` em `editor/core/serializacao_util.py`, executando os testes unitários até atingir 100% de aprovação e cobertura verde

## 3. Limpeza Incondicional no Protobuf e Integração no CroquiModel

- [x] 3.1 Atualizar `CroquiModel.extrair_arquivos_e_serializar` em `editor/models/croqui_model.py` para limpar incondicionalmente a extensão `ext_metadados_arquivo` em `croqui_msg_copy` para `pico.mapas_gerais`, `sg.setor`, `sg.grupo`, `setores` internos de grupos, `botao.destino.secao_textual` e na raiz `Croqui`, mesmo quando o elemento possuir apenas `caminho`
- [x] 3.2 Aplicar a função `sanitizar_dicionario_sem_extensoes` no dicionário resultante em `extrair_arquivos_e_serializar` e nos dicionários de frontmatter em `_salvar_objeto_com_frontmatter`
- [x] 3.3 Tratar falhas de leitura em `CroquiModel.carregar_arquivos_externos` para assegurar que extensões não permaneçam em nós externos cujo conteúdo não foi carregado
- [x] 3.4 Executar a suíte de testes unitários `editor/models/croqui_model_test.py` e assegurar 100% de cobertura verde

## 4. Verificação de Integridade, Contrato e Cobertura

- [x] 4.1 Executar a suíte de testes de contrato `tests/contrato_editor_serializacao_test.py` e verificar que todos os cenários passam com sucesso (Green)
- [x] 4.2 Executar a suíte de testes do editor via pytest e validar 100% de unit test coverage e ausência de regressões
