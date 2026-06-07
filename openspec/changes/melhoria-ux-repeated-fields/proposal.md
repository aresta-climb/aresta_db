## Why

O formulário do editor (em PyQt) atualmente apresenta travamentos (cerca de 0.5s de delay na abertura) ao carregar itens pesados, como Setores que possuem dezenas de metadados aninhados em listas (`repeated fields`). Isso ocorre porque todos os widgets são instanciados sincronamente na thread de UI. Além do travamento, a interface fica poluída e difícil de ler com todos os subformulários totalmente abertos.

## What Changes

- Implementar blocos colapsáveis (Acordeão) para itens em `repeated fields`. Os itens iniciarão colapsados.
- Implementar renderização sob demanda (Lazy Loading): Os widgets internos de um subformulário só serão instanciados no Qt quando o usuário expandir o acordeão pela primeira vez, resolvendo a lentidão.
- Implementar uma heurística de leitura no título do acordeão: buscar valores em campos-chave (como `id`, `nome`, `titulo`) para exibir no cabeçalho do acordeão fechado (ex: `▶ Item 1 - Id: 07`), caso contrário, exibir apenas o índice.

## Capabilities

### New Capabilities
- `lazy-repeated-fields`: Melhoria de UX e performance na listagem e edição de campos repetidos no editor de dados, introduzindo comportamento colapsável e carregamento sob demanda dos formulários aninhados.

### Modified Capabilities
- Nenhuma

## Impact

- Principal impacto no módulo `editor/views/widget_editor_dados.py`, que centraliza a montagem de formulários dinâmicos.
- O novo padrão afetará todas as telas que exibem propriedades que são `repeated fields` complexos (PontoDeInteresse, Escalada, etc.).
