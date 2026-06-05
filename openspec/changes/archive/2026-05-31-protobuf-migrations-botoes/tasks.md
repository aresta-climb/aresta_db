## 1. Schema & Protos

- [x] 1.1 Adicionar o campo `int32 ultima_migracao = 15;` em `croqui.proto` (dentro da mensagem `Croqui`) e anotação `[(aresta.formato_na_ui) = INVISIVEL]`.
- [x] 1.2 Compilar os arquivos proto executando `python build.py protos --force`.

## 2. Motor de Migração & Helpers

- [x] 2.1 Criar a biblioteca auxiliar de testes em `scripts/helpers_migracao.py` com funções de setup de croqui temporário.
- [x] 2.2 Criar o motor em `scripts/migrador.py` com detecção numérica de arquivos `.py` sob a pasta `migracoes/` e importação dinâmica via `importlib.util`.

## 3. Primeira Migração (Seções para Botões) e Testes

- [x] 3.1 Criar o script de migração `/migracoes/0001_migrar_secoes_para_botoes.py` para converter `secoes_textuais` / `arquivos_markdown` em `botoes`.
- [x] 3.2 Criar o arquivo de testes correspondente `/migracoes/0001_migrar_secoes_para_botoes_test.py`.
- [x] 3.2.1 Criar um teste unitário global em `migracoes/` para validar a unicidade de IDs sequenciais (prefixos de 4 dígitos) de todos os arquivos de migração.
- [x] 3.3 Modificar o [build.py](file:///c:/Renato/Devel/aresta/aresta_db/build.py) para incluir a pasta `migracoes` nos caminhos de teste executados pelo Pytest.

- [x] 3.4 Rodar os testes via `python build.py test` para confirmar o funcionamento da primeira migração e do helper.


## 4. Integração com a Compilação e com o Editor

- [x] 4.1 Modificar o arquivo [preparar_submissao_lib.py](file:///c:/Renato/Devel/aresta/aresta_db/scripts/preparar_submissao_lib.py) para executar `aplicar_migracoes` no início de `corrigir_database` e adaptar as referências de `secoes_textuais` para usar a nova estrutura de `botoes`.
- [x] 4.2 Modificar o arquivo [area_principal.py](file:///c:/Renato/Devel/aresta/aresta_db/editor/views/area_principal.py) no editor para rodar `aplicar_migracoes` ao carregar um croqui e atualizar as rotinas de carga/salvamento para lidar com `botoes` e `DestinoBotao`.

## 5. Validação e Homologação Final

- [x] 5.1 Executar a suíte completa de testes (`python build.py test`) para confirmar que nada foi quebrado e todas as migrações passam de forma limpa.
- [x] 5.2 Rodar o deploy oficial (`python build.py deploy`) para validar que todos os croquis reais da database local foram migrados com sucesso e geraram novos arquivos compilados perfeitamente.

## 6. Melhorias de Robustez e Cobertura de Testes

- [x] 6.1 Implementar `obter_ultima_versao_migracao()` em `scripts/migrador.py`.
- [x] 6.2 Integrar a gravação de `ultima_migracao` em novos croquis no editor (`croqui_experimental.py`).
- [x] 6.3 Atualizar as diretrizes do workflow `.agents/workflows/converter_pdf_para_croqui.md` para instruir o preenchimento de `ultima_migracao`.
- [x] 6.4 Mover o teste de unicidade de IDs de `migracoes/` para `tests/unicidade_ids_test.py`.
- [x] 6.5 Garantir idempotência e testes correspondentes em `0001_migrar_secoes_para_botoes_test.py` (cobrindo inclusive cenários sem `ultima_migracao` definida).
- [x] 6.6 Criar novos testes unitários e de integração ao lado dos arquivos modificados: `scripts/migrador_test.py` e `scripts/helpers_migracao_test.py`.
- [x] 6.7 Adicionar testes de cobertura em `build_test.py`, `preparar_submissao_lib_test.py` e um teste e2e de migração automática no editor em `area_principal_e2e_test.py`.
- [x] 6.8 Executar a suíte de testes finais (265 testes) e validar a integridade da base local com `build.py deploy`.

