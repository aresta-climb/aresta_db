## 1. Testes de Integração e Unitários (TDD)

- [x] 1.1 Adicionar casos de teste em `scripts/preparar_submissao_lib_test.py` para validar referências de mapa.
- [x] 1.2 Criar um teste que falha ao referenciar um ID inexistente em um Setor.
- [x] 1.3 Criar um teste que falha ao referenciar um ID inexistente em um Grupo.
- [x] 1.4 Criar um teste que passa quando todos os IDs existem em pelo menos um mapa do contexto.

## 2. Implementação da Validação (Library-First)

- [x] 2.1 Implementar `validar_referencias_mapa(croqui)` em `scripts/preparar_submissao_lib.py`.
- [x] 2.2 Implementar lógica para coletar todos os IDs de mapas em Setores e Grupos.
- [x] 2.3 Implementar varredura de todas as escaladas (`ViaEsportiva`, `ViaMovel`, `Boulder`, `ViaMultiplasEnfiadas`, `Highline`).
- [x] 2.4 Retornar uma lista de strings com descrições detalhadas dos erros encontrados.

## 3. Integração no Pipeline de Deploy

- [x] 3.1 Modificar `scripts/deploy_generated.py` para chamar `validar_referencias_mapa` durante a compilação.
- [x] 3.2 Implementar o acúmulo de erros de validação por croqui no loop de compilação.
- [x] 3.3 Garantir que o script continue processando outros croquis após uma falha de validação.
- [x] 3.4 Atualizar o log final para mostrar o número total de falhas e sucessos.

## 4. Verificação e Refatoração

- [x] 4.1 Garantir que todos os testes passem com `pytest scripts/preparar_submissao_lib_test.py`.
- [x] 4.2 Executar um deploy simulado com erros para verificar a saída no terminal.
- [x] 4.3 Revisar o código seguindo `PRINCIPIOS.md` (Simplicidade e Português).
