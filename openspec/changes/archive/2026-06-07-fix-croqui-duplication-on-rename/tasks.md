## 1. Testes Automatizados (Fase Red - TDD)

- [ ] 1.1 Atualizar `area_principal_test.py` criando teste de integração validando a chamada de `renomear_pasta_croqui` ao alterar o ID do croqui.
- [ ] 1.2 Atualizar `croqui_experimental_test.py` com testes unitários confirmando a gravação de `id_original` e o comportamento do método `renomear_pasta_croqui`.
- [ ] 1.3 Atualizar `worker_test.py` garantindo que o publicador consulta `id_original` e aciona remoção da cópia anterior.

## 2. Modificações na Gestão Local de Repositório

- [ ] 2.1 Incluir parâmetro `id_original` na criação e importação do croqui e persistir no `croqui_experimental.yaml` (`editor/core/croqui_experimental.py`).
- [ ] 2.2 Implementar rotina `renomear_pasta_croqui(caminho_raiz, novo_id)` protegida contra bloqueios do S.O. (`editor/core/croqui_experimental.py`).

## 3. Integração com Interface e Publicador

- [ ] 3.1 Acoplar na `JanelaPrincipal.salvar_croqui()` a verificação de alteração do ID e comandar a renomeação da pasta física antes da gravação do novo yaml (`editor/legacy_views/area_principal.py`).
- [ ] 3.2 Editar `TarefaPublicacao.run()` para validar o `id_original` e deletar via sistema de arquivos e index do git a pasta ancestral, mitigando a duplicação no repositório final (`editor/core/worker.py`).
