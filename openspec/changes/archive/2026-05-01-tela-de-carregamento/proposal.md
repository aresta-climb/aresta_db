## Why

A interface atual da "Página Inicial" ocupa todo o espaço da janela principal, o que não é ideal para um ponto de entrada rápido. Renomear para "Tela de Carregamento" e transformar em um diálogo compacto permite uma experiência mais focada e profissional.

## What Changes

- **Transformação em QDialog**: A tela passou de um widget embutido para um diálogo flutuante.
- **Nomes dos Botões**: Restauração dos nomes completos ("Novo croqui", "Importar croqui experimental", "Editar croqui oficial").
- **Layout**: Estrutura em duas partes com histórico e mensagem de estado vazio.
- **Integração**: Atualização do fluxo no `main.py` para exibição modal.

## Capabilities

### New Capabilities
- Nenhuma.

### Modified Capabilities
- `editor-pagina-inicial`: Atualizada para os novos requisitos de layout compacto e mensagem de estado vazio. A especificação também será renomeada para `editor-tela-de-carregamento`.

## Impact

- `editor/views/pagina_inicial.py` (Deletado)
- `editor/views/tela_de_carregamento.py` (Novo)
- `editor/views/pagina_inicial_test.py` (Deletado)
- `editor/views/tela_de_carregamento_test.py` (Novo)
- `editor/main.py` (Modificado para usar a nova view)
- `openspec/specs/editor-pagina-inicial/spec.md` (Modificado/Renomeado)
