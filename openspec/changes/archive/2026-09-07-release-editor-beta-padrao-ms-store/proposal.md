## Why

Atualmente, o workflow de lançamento do Editor Aresta (`release-editor.yml`) sempre compila duas vezes com PyInstaller (produção e beta), gera dois pacotes MSIX e realiza upload para o Partner Center da Microsoft Store com a flag `--noCommit`. Isso torna todo ciclo de release lento (15 a 20 minutos no runner Windows) mesmo quando a intenção é apenas disponibilizar uma versão de testes no canal Beta. Além disso, o envio como rascunho (`--noCommit`) obriga o mantenedor a acessar manualmente o painel web do Microsoft Partner Center para submeter a atualização para revisão.

Esta mudança desacopla a publicação rotineira no canal Beta da publicação na loja, tornando o fluxo Beta padrão e muito mais rápido (~5 minutos com uma única compilação PyInstaller), além de oferecer um parâmetro explícito no workflow para lançar na Microsoft Store já com submissão direta para certificação/revisão (dispensando qualquer ação manual no painel da Microsoft).

## What Changes

- **Padrão Beta-Only**: O workflow passa a compilar e publicar por padrão apenas no canal Beta (Cloudflare R2 e AppInstaller), reduzindo drasticamente o tempo de CI ao rodar o PyInstaller uma única vez.
- **Opção Direta para Microsoft Store**: Adição do input booleano `publicar_microsoft_store` (padrão: `false`). Quando marcado como `true`, compila a versão oficial de produção, gera o MSIX e executa `msstore publish` diretamente para revisão (sem a flag `--noCommit`).
- **Remoção de Submissão em Rascunho**: Substituição do antigo input `should_publish` por `publicar_microsoft_store`, garantindo que qualquer submissão para a loja seja enviada diretamente para a fila de certificação.
- **Ordenação Otimizada**: O fluxo do canal Beta é executado primeiro. As etapas da Microsoft Store rodam de maneira condicional logo após o Beta.
- **Atualização dos Testes Arquiteturais**: Atualização e expansão de `tests/workflow_release_editor_test.py` para validar a nova entrada, as condições dos passos e o comportamento do comando de publicação.

## Capabilities

### New Capabilities
- `editor-workflow-release`: Especifica os requisitos do workflow de lançamento do Editor Aresta, cobrindo o canal Beta como publicação padrão acelerada e a submissão condicional direta para certificação na Microsoft Store.

### Modified Capabilities

## Impact

- `.github/workflows/release-editor.yml`: Ajuste nos inputs do `workflow_dispatch`, condicionamento dos passos de produção/loja e remoção da flag `--noCommit`.
- `tests/workflow_release_editor_test.py`: Atualização dos testes unitários que inspecionam o YAML do workflow para assegurar integridade arquitetural.
