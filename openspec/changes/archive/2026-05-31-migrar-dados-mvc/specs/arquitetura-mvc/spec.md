## ADDED Requirements

### Requirement: Estrutura de Diretórios MVC
O módulo `editor` do Aresta Editor DEVE implementar uma estrutura estrita baseada no padrão Model-View-Controller orientada a Comandos. O código de interface antiga que não adere a este padrão DEVE ser movido para um diretório de isolamento legado.

#### Scenario: Organização do Código Fonte
- **WHEN** um agente ou desenvolvedor adicionar ou modificar código para a aba de Dados
- **THEN** os arquivos DEVEM ser organizados nas sub-pastas `models/`, `views/`, `controllers/` ou `commands/` dentro de `editor/`, e o código que não segue MVC (como os de Mapas e Imagens) DEVE estar em `legacy_views/`.

### Requirement: Encapsulamento Restrito das Mutações do Model
O Model DEVE atuar como a fonte única da verdade e isolar estritamente seu acesso de escrita para evitar concorrência e loops na UI. Os métodos que provocam alteração de estado interno DEVEM ser convencionados como restritos.

#### Scenario: Acesso de Leitura pela Interface
- **WHEN** a View (ou o Controller) precisar ler um valor para preencher campos visuais
- **THEN** ela DEVE chamar os métodos ou propriedades públicas de leitura do Model, os quais não possuem restrição de acesso.

#### Scenario: Mutação do Estado Controlada
- **WHEN** o sistema precisar alterar um valor dentro do Model
- **THEN** a mutação DEVE ser feita exclusivamente pela invocação dos métodos prefixados com `_` (ex: `_set_atributo`), sendo obrigatório que as únicas classes a invocá-los sejam as que residem na camada de `commands/`. A View e o Controller NUNCA devem acessar tais métodos diretamente.

### Requirement: Proteção de Arquitetura Baseada em AST
O sistema DEVE incorporar uma verificação automatizada de análise estática de código para impedir a regressão da arquitetura, de forma análoga a padrões como ArchUnit em outras linguagens.

#### Scenario: Violação do Contrato de Mutação
- **WHEN** qualquer arquivo fora da pasta `models/` e da pasta `commands/` tenta invocar um método mutador restrito do Model (iniciado com `_set_`)
- **THEN** a suíte de testes (ex: `editor/arquitetura_mvc_test.py`) utilizando parsing de Árvore Sintática Abstrata (AST) DEVE falhar a etapa de build contínua e reportar o acesso ilegal.
