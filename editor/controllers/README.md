# Controllers

O Controller é a ponte lógica entre as intenções da UI (View) e as mutações do Histórico (Commands).

**Regras:**
1. A View chama o Controller passando parâmetros simples.
2. O Controller valida a intenção, constrói as dependências do `QUndoCommand` apropriado e o envia para o Gerenciador de Histórico da aplicação.
3. Controllers não manipulam o Model de forma direta (não chamam `_set_*`), deixando essa responsabilidade exclusiva para os Comandos de Histórico que serão executados pela `QUndoStack`.
