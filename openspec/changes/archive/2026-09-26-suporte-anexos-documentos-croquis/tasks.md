## 1. Extração e Dados de São João Del Rei

- [x] 1.1 Extrair as páginas 69 e 70 do arquivo `croqui_original.pdf` gerando os arquivos limpos `ficha_autorizacao_cemonta.pdf` e `termo_reconhecimento_riscos_cemonta.pdf` dentro de `database/br_mg_sao_joao_del_rei_serra_do_lenheiro/anexos/` e verificar integridade dos arquivos gerados via script de validação
- [x] 1.2 Atualizar o arquivo `database/br_mg_sao_joao_del_rei_serra_do_lenheiro/anexo_regras_cemonta.md` substituindo o link externo do Google Drive por links de botões Markdown apontando para `anexos/ficha_autorizacao_cemonta.pdf` e `anexos/termo_reconhecimento_riscos_cemonta.pdf`

## 2. Pipeline de Deploy, Serving e Checksums

- [x] 2.1 [TDD Red] Criar testes em `scripts/deploy_generated_test.py` verificando que a pasta `anexos/` é copiada para o diretório `generated/<croqui_id>/anexos/` e que seus arquivos são indexados com SHA-256 no campo `arquivos_externos` do `compilado.binarypb`
- [x] 2.2 [TDD Green] Implementar no `passo_a_compilar_croquis` de `scripts/deploy_generated.py` a cópia e cálculo de hash SHA-256 de todos os arquivos da pasta `anexos/`
- [x] 2.3 [TDD Red] Criar testes em `scripts/calcular_tamanho_croqui_lib_test.py` validando que os arquivos contidos em pastas de anexos são contabilizados na soma de bytes do croqui
- [x] 2.4 [TDD Green] Atualizar a função `calcular_tamanho_croqui_bytes` em `scripts/calcular_tamanho_croqui_lib.py` para aceitar e somar diretórios ou listas de arquivos de anexos
- [x] 2.5 [TDD Red] Criar teste em `serving/update_serving_test.py` verificando que extensões `.pdf` recebem `ContentType: application/pdf` no método `_upload_file` e que caminhos de `anexos/` presentes no `arquivos_serving.yaml` são enviados no delta deploy
- [x] 2.6 [TDD Green] Atualizar a detecção de Content-Type em `serving/update_serving.py` adicionando suporte a `.pdf` e formatos de documentos

## 3. Editor Desktop: Diálogo e Ação de Inserção de Botão

- [x] 3.1 [TDD Red] Criar testes unitários em `editor/commands/comandos_protobuf_test.py` para o comando `CmdInserirBotaoMarkdown` validando inserção de texto, inclusão transacional de arquivo anexo no modelo, Undo e Redo
- [x] 3.2 [TDD Green] Implementar `CmdInserirBotaoMarkdown` em `editor/commands/comandos_protobuf.py` e método facilitador `inserir_botao_markdown` no `CroquiController`
- [x] 3.3 [TDD Red] Criar testes unitários em `editor/views/dialogos/dialogo_inserir_botao_markdown_test.py` testando layout, listagem de anexos existentes, importação de arquivo externo e geração de tag Markdown
- [x] 3.4 [TDD Green] Implementar `DialogoInserirBotaoMarkdown` em `editor/views/dialogos/dialogo_inserir_botao_markdown.py`
- [x] 3.5 [TDD Red] Criar testes em `editor/views/widget_editor_dados_test.py` validando a existência do botão "Inserir Botão" no `WidgetEditorMarkdown` e o disparo do diálogo com inserção de texto no cursor
- [x] 3.6 [TDD Green] Conectar o botão `btn_inserir_botao` no layout de cabeçalho do `WidgetEditorMarkdown` em `editor/views/widget_editor_dados.py`

## 4. Validação e Verificação Integrada

- [x] 4.1 Executar compilação completa de deploy (`python scripts/deploy_generated.py`) e verificar que `generated/br_mg_sao_joao_del_rei_serra_do_lenheiro/anexos/` é gerado e que os arquivos constam no `generated/arquivos_serving.yaml`
- [x] 4.2 Executar a validação de cabeçalhos e licenças (`python scripts/validador_cabecalhos.py`) e toda a suíte de testes (`python build.py test`) garantindo 100% de testes passando e conformidade com o `AGENTS.md`
