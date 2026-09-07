## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 1.1 Criar teste de integração inicial em `editor/core/salvamento_estruturas_vazias_integracao_test.py` verificando o contrato ponta a ponta: salvamento e compilação de um croqui experimental contendo um novo Pico sem setores e um novo Grupo com lista de setores vazia (Fase Vermelha - falha esperada).

## 2. Compilação e Expansão de Estruturas Vazias (TDD)

- [x] 2.1 Criar testes unitários em `scripts/preparar_submissao_lib_test.py` para a expansão de grupo com lista `setores: []`, verificando que o tipo `grupo` é preservado e não rebaixado para setor (Fase Vermelha).
- [x] 2.2 Atualizar `expandir_arquivo_generico` em `scripts/preparar_submissao_lib.py` para respeitar o tipo declarado e a presença da chave `setores` vazia (Fase Verde).
- [x] 2.3 Criar testes unitários em `scripts/gerar_compilado_md_test.py` cobrindo cenários com Picos vazios, Grupos sem setores e nós compilados nulos (Fase Vermelha).
- [x] 2.4 Implementar tratamento seguro contra nulos e suporte a listas vazias em `scripts/gerar_compilado_md.py` (Fase Verde).

## 3. Preservação de Rastreamento de Exceções

- [x] 3.1 Criar testes unitários em `scripts/deploy_generated_test.py` verificando o encadeamento de exceções (`raise ... from e`) e o registro do rastreamento completo no console (Fase Vermelha).
- [x] 3.2 Atualizar o tratamento de exceções no laço de compilação de `scripts/deploy_generated.py` para registrar `traceback.format_exc()` e re-lançar com encadeamento causal `from e` (Fase Verde).
- [x] 3.3 Atualizar `editor/core/worker.py` (`TarefaSalvamento`) para capturar e transmitir o rastreamento técnico estruturado no sinal de erro.

## 4. Biblioteca de Diálogo Amigável de Erro de Salvamento (Library-First)

- [x] 4.1 Criar testes unitários em `editor/views/dialogo_erro_salvamento_test.py` validando a construção do diálogo com mensagem amigável, texto informativo, detalhes técnicos expansíveis e ação de cópia (Fase Vermelha).
- [x] 4.2 Implementar a nova biblioteca independente `editor/views/dialogo_erro_salvamento.py` com a função `exibir_dialogo_erro_salvamento` (Fase Verde).
- [x] 4.3 Integrar a nova biblioteca em `editor/legacy_views/area_principal.py` no manipulador `_on_salvar_erro` e atualizar `editor/legacy_views/area_principal_test.py`.

## 5. Verificação de Cobertura e Integração Final

- [x] 5.1 Executar os testes de integração criados na Fase 1 e certificar que passam integralmente (Fase Verde da Integração).
- [x] 5.2 Executar a suíte de testes com medição de cobertura e garantir 100% de cobertura nos arquivos novos e modificados conforme o Princípio III.
