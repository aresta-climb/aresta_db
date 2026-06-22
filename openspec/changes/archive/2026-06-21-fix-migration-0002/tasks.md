## 1. TDD: Testes em Primeiro Lugar (Vermelho-Verde-Refatorar)

- [x] 1.1 **Fase Red**: Adicionar teste para validação simples contra múltiplos mapas (quando não usar `/`). Confirmar que falha.
- [x] 1.2 **Fase Red**: Adicionar teste de distribuição estrita por índice de mapa para IDs com o separador `/`. Confirmar que falha.
- [x] 1.3 **Fase Red**: Adicionar testes para validação de parse alfanumérico (letras e números separados). Confirmar que falha.
- [x] 1.4 **Fase Red**: Adicionar testes garantindo a geração de `ids_no_mapa_nao_encontrados.yaml` quando houver falhas totais e parciais. Confirmar que falha.

## 2. Implementação do Script de Migração (Fase Green/Refactor)

- [x] 2.1 Refatorar extração: implementar parsing de `/` e separar strings compostas em "grupos de IDs" (ex: "2B" vira `["2", "B"]`). Fazer os testes de parsing passarem.
- [x] 2.2 Refatorar roteamento: implementar correspondência estrita (com verificação dos `pontos_de_interesse`) para casos de via simples vs vias com sub-grupos. Fazer os testes de roteamento passarem.
- [x] 2.3 Implementar acúmulo de falhas de IDs em memória e o gravador final do `ids_no_mapa_nao_encontrados.yaml`.
- [x] 2.4 **Verificação de Cobertura**: Rodar `pytest --cov=migracoes migracoes/0002_centralizar_map_references_test.py` e **garantir 100% de coverage**. Caso contrário, escrever mais testes.

## 3. Execução

- [x] 3.1 Rodar a nova migração na pasta `database/` completa (`python migracoes/0002_centralizar_map_references.py database/`).
- [x] 3.2 Verificar manualmente `git status` e `git diff` para garantir que `ids_no_mapa_nao_encontrados.yaml` foi gerado quando necessário, e os dados migrados estão precisos.
