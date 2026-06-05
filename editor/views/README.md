# Views

As Views aqui contidas devem ser "Burras".
Isso significa que elas NÃO contêm lógica de negócio e NÃO manipulam os dados diretamente.

**Regras:**
1. **Puxar (Pull):** A View lê do Model (`get_nome()`) para renderizar seu estado inicial.
2. **Ouvir (Push):** A View assina os Sinais emitidos pelo Model para se atualizar automaticamente quando os dados mudam em back-ground (Undo/Redo).
3. **Sem Mutação:** Views NUNCA chamam os métodos `_set_*` do Model.
4. **Despachar Ações:** Quando o usuário clica ou digita algo, a View apenas despacha a sua intenção (`controller.atualizar_nome(novo_nome)`), sem saber ou se importar de como os dados serão armazenados.
