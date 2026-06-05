## 1. Implementação do Core (Library-First)

- [x] 1.1 Criar `editor/core/croqui_format_test.py` com testes de unidade para ofuscação e integridade de ZIP.
- [x] 1.2 Implementar `editor/core/croqui_format.py` com as funções de empacotamento e leitura ofuscada.
- [x] 1.3 Garantir que os testes do core estejam passando (Red-Green-Refactor).

## 2. Funcionalidade de Exportação

- [x] 2.1 Corrigir o diálogo de salvamento em `editor/views/area_principal.py` para usar a extensão `.croqui`.
- [x] 2.2 Implementar a tarefa de background para exportação no controller/view.
- [x] 2.3 Adicionar indicadores de progresso e mensagens de sucesso/erro.

## 3. Funcionalidade de Importação

- [x] 3.1 Refatorar a lógica de importação na `TelaDeCarregamento` para usar `croqui_format.ler_croqui`.
- [x] 3.2 Garantir suporte retroativo ou fallback para arquivos `.zip` puros (opcional, mas recomendado).
- [x] 3.3 Validar que o histórico de croquis é atualizado corretamente após a importação ofuscada.

## 4. Verificação e Polimento

- [x] 4.1 Realizar testes de integração ponta a ponta (Exportar -> Importar).
- [x] 4.2 Verificar conformidade com os princípios Aresta (nomes em português, etc).
