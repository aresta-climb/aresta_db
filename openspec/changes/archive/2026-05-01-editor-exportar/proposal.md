## Why

O botão de exportar croqui no editor está atualmente inoperante ou apresenta erros após a seleção do arquivo. Além disso, o formato de arquivo `.croqui` precisa ser implementado seguindo a especificação de um ZIP com o magic number ofuscado para garantir que o arquivo seja reconhecido apenas pelo ecossistema Aresta.

## What Changes

- Implementação completa da funcionalidade de exportação de croquis experimentais.
- Criação de um arquivo ZIP compactado da pasta do croqui, renomeado para `.croqui`.
- Ofuscação do magic number do ZIP (XOR no primeiro byte com `0xFF`) para "quebrar" a detecção automática de ZIP por outros apps.
- Correção do fluxo de interface do usuário no botão de exportar (diálogo de salvamento).
- Atualização da lógica de importação na tela de carregamento para lidar com o formato ofuscado.

## Capabilities

### New Capabilities
- `exportacao-croqui`: Implementa a funcionalidade de gerar o arquivo `.croqui` a partir de uma pasta de croqui experimental.

### Modified Capabilities
- `croqui-experimental-format`: Adiciona o requisito de ofuscação do magic number no formato de exportação `.croqui`.
- `editor-tela-de-carregamento`: Atualiza o requisito de importação para suportar a desofuscação do formato `.croqui`.

## Impact

- `editor/views/area_principal.py`: Onde o botão de exportar está localizado.
- `editor/views/tela_de_carregamento.py`: Onde a funcionalidade de importar está localizada.
- `editor/core/`: Possível criação de uma biblioteca de utilitários para manipulação de arquivos `.croqui`.
- Estabilidade do sistema de arquivos e portabilidade de croquis experimentais.
