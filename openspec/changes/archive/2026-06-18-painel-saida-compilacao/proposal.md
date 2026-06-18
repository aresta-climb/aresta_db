## Why

Atualmente, ao salvar um croqui no editor e ocorrerem erros ou avisos na compilação, uma janela modal bloqueante (`DialogoErrosCompilacao`) é exibida. Isso interrompe o fluxo de trabalho do usuário, que precisa fechar a janela para voltar a editar o croqui e corrigir os problemas. A substituição por um painel não-bloqueante na parte inferior da interface (estilo VS Code) visa melhorar a fluidez e a experiência do usuário durante o processo iterativo de ajuste e compilação de croquis.

## What Changes

- Remoção do `DialogoErrosCompilacao` bloqueante que aparecia após o salvamento com falhas.
- Adição de um painel de saída acoplável (`QDockWidget`) na parte inferior da `JanelaPrincipal`.
- Exibição de erros e avisos formatados, permitindo consulta contínua enquanto o usuário corrige os dados.
- Ocultamento automático do painel em caso de compilação 100% bem sucedida.

## Capabilities

### New Capabilities
- `compilation-output-panel`: Gerencia a exibição não-bloqueante de resultados de compilação, estilização de erros/avisos (com cores em tons pastel) e o comportamento dinâmico de exibição do painel acoplável.

### Modified Capabilities

- Nenhuma.

## Impact

- O fluxo de salvamento do `editor` em `JanelaPrincipal` não interromperá mais o usuário com modais.
- `DialogoErrosCompilacao` será descontinuado.
