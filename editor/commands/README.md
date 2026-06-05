# Commands

A camada `commands/` contém todos os `QUndoCommand`s do projeto.
Ela é a **única** camada privilegiada que tem autorização arquitetural para mutar os dados dentro da pasta `models/`.

**Regras:**
1. **Mutação Restrita:** Classes de Comando chamam os métodos `_set_*` do Model durante o `redo()`, e invertem a operação chamando os mesmos métodos no `undo()`.
2. **Isolamento:** Nenhuma interface visual (View) ou Controller deve herdar ou implementar Comandos diretamente dentro de seus módulos. Todos os comandos ficam aqui.
