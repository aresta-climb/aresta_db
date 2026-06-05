# Models

A camada `models` é a fonte da verdade da aba. Ela encapsula a árvore Protobuf e fornece uma interface segura para o restante do sistema.

**Regras estritas:**
1. **Views leem, mas não escrevem:** Views e Controllers podem invocar métodos como `get_nome()` para exibir informações.
2. **Encapsulamento de Escrita:** Qualquer método que altere o estado interno do Model DEVE ser prefixado com sublinhado, ex: `_set_nome()`.
3. **Privilégio Exclusivo:** Os métodos `_set_*` SÓ PODEM ser invocados por classes dentro da pasta `commands/`. Nunca mude o Model a partir da View ou Controller.
4. **Notificação:** Sempre que o estado mudar, o Model deve emitir os Sinais PyQt correspondentes para que a View se atualize automaticamente.
5. **Estado Privado:** Use `__func` (duplo sublinhado) para métodos puramente internos da classe Model que nem os `commands/` deveriam acessar.
