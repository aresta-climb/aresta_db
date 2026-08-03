## Context

A aba de Dados do Editor Aresta (liderada pelo `WidgetEditorDados`) atualmente mistura a lógica de interface do usuário, a estruturação dos dados (Protobuf) e a geração de comandos de histórico (`QUndoCommand`). Esse acoplamento causa fragilidade (risco de loops de eventos), torna a inclusão de testes complexa e dificulta a evolução do código. A refatoração MVC (Model-View-Controller) visa isolar as responsabilidades de forma definitiva e serve como projeto-piloto para uma futura migração de outras abas mais complexas como Mapas e Imagens.

## Goals / Non-Goals

**Goals:**
- Implementar uma arquitetura de pastas estrita baseada no padrão MVC: `models/`, `views/`, `controllers/`, e `commands/`.
- Garantir que as Views não façam mutações diretas nos Models, funcionando apenas como despachantes de intenção para os Controllers.
- Encapsular a mutação dos Models (via prefixo `_` em Python) para que seja chamada apenas pelas classes em `commands/`.
- Validar essa arquitetura em CI/CD usando análise estática de código (AST).

**Non-Goals:**
- Refatorar a aba de Mapas ou a aba de Imagens. Elas permanecerão operando na arquitetura antiga e serão movidas para a pasta `legacy_views/`.
- Adicionar funcionalidades de negócio à interface gráfica. O foco é estritamente arquitetural.
- Migrar do `QUndoStack` do PyQt para outro gerenciador de estado.

## Decisions

- **Separação de Pastas e Nomenclatura**: A divisão em 4 subpastas claras com `README.md` específicos. As views atuais que não aderem ao modelo irão para `legacy_views/`. Essa decisão segrega o legado do novo padrão de forma transparente, permitindo que a transição ocorra gradualmente nos próprios passos do projeto sem quebrar o que já funciona.
- **Proteção do Model e Regras de Encapsulamento**: O Python não possui o conceito nativo de proteção estrita como `private` ou `protected` em C++ ou Java. Optou-se por utilizar convenções associadas ao linting. Métodos de mutação estritamente privados ao model usarão `__func` (duplo sublinhado para name mangling), enquanto métodos mutadores voltados para Comandos serão prefixados com `_set_`. O `README.md` estabelece a regra de negócio de que apenas a pasta `commands/` acessa os métodos `_set_`. A View poderá ler atributos diretamente ou com getters públicos.
- **Testes Arquiteturais (AST)**: optamos por testes baseados em AST (Abstract Syntax Tree) usando o script `editor/arquitetura_mvc_test.py` na raiz do módulo editor. O script lerá todo o código do aplicativo e bloqueará se algum método `_set_*` da pasta `models` estiver sendo invocado de fora da pasta `models` ou da pasta `commands`.
- **Aderência aos Princípios (PRINCIPIOS.md)**: A arquitetura adota rigorosamente os princípios do repositório, em especial a "Simplicidade e Anti-Abstração" (isolando o estado Protobuf de abstrações acopladas na UI) e a regra de "Edições de Estado via Comandos do Histórico" (todo mutador passará obrigatória e exclusivamente por comandos coordenados).

## Risks / Trade-offs

- **[Risco] O refatoramento pode quebrar interações visuais existentes na aba de Dados.**
  - **Mitigação**: Os `QUndoCommand`s já existentes serão reutilizados, apenas realocados. Ao transformar o `WidgetEditorDados` em uma "View Burra", dependemos menos de lógica UI e mais da lógica no Controller, que será validada pela re-execução dos testes antigos.
- **[Risco] Mover as views antigas para `legacy_views` pode gerar dependências circulares ou quebrar importações de terceiros.**
  - **Mitigação**: O commit da migração de pastas cuidará estritamente das importações no `area_principal.py` (o orquestrador) e nos arquivos do módulo. Testes rigorosos de carga de sistema devem ser realizados.
- **[Risco] A curva de aprendizado da barreira de encapsulamento em Python pode confundir contribuidores.**
  - **Mitigação**: Adição obrigatória dos arquivos `README.md` descritivos servirá como um manifesto de "como programar no Editor Aresta" em cada pasta do MVC.
