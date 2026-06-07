## Why

Ao alterar o ID de um croqui pela interface do editor, o sistema atualizava apenas os metadados do arquivo YAML, sem renomear a pasta raiz local correspondente (que mantinha o id antigo) e sem instruir a remoção da pasta anterior no repositório oficial na hora de criar um Pull Request. Isso gerava uma cópia duplicada (croqui com id antigo e outro com novo) perdendo o histórico. Corrigimos esse problema para manter a integridade dos croquis.

## What Changes

- O sistema gravará um metadado `id_original` localmente sempre que importar ou criar um croqui.
- Ao clicar em "Salvar", se o ID do croqui for alterado no modelo, a pasta experimental subjacente também será renomeada (mantendo o timestamp).
- Durante o fluxo de "Publicar", a rotina validará o `id_original` contra o novo ID e efetuará um `git rm` do diretório correspondente ao id antigo no repositório principal clonado.

## Capabilities

### New Capabilities
- `croqui-rename`: A capacidade estrutural do editor rastrear e executar com consistência a alteração de IDs tanto na pasta local quanto no tracking do repositório remoto.

### Modified Capabilities
- `croqui-publishing`: A rotina de empacotamento e sincronização com o Github foi aprimorada para detectar e enviar a exclusão do nó de dados antigo (ancestralidade via id_original).

## Impact

- Módulo UI do editor (`area_principal.py`).
- Backend do repositório local (`croqui_experimental.py`).
- Worker de integração git (`worker.py`).
- Extensão nos testes de integração e unitários em conformidade com TDD.
