## Context

O arquivo `.github/workflows/release-editor.yml` é responsável pelo ciclo de vida de compilação, empacotamento MSIX, assinatura e publicação do Editor Aresta para Windows. Anteriormente, o fluxo executava linearmente a compilação do executável de produção e o envio para a Microsoft Store com a opção `--noCommit` antes de processar o canal Beta.

## Goals / Non-Goals

**Goals:**
- Configurar o canal Beta como publicação padrão, reduzindo o tempo de CI ao rodar o PyInstaller apenas uma vez (~5 minutos).
- Reordenar as etapas para que o canal Beta execute primeiro.
- Adicionar o input `publicar_microsoft_store` (booleano, padrão `false`) no `workflow_dispatch`.
- Condicionar as etapas de produção e Microsoft Store a `${{ inputs.publicar_microsoft_store }}`.
- Submeter diretamente para revisão e certificação na Microsoft Store (sem `--noCommit`) sempre que a opção for marcada.
- Assegurar a atomicidade do ciclo git (push de tag e versão `-dev`) apenas após a conclusão com sucesso de todos os passos ativos.
- Expandir e atualizar os testes arquiteturais em `tests/workflow_release_editor_test.py`.

**Non-Goals:**
- Não alterar a lógica dos scripts de build em Python (`editor/build.py`, `EditorAresta.spec` ou ferramentas de empacotamento).
- Não criar múltiplos jobs paralelos de runner, preservando a simplicidade (Princípio VI) e o consumo de minutos do runner Windows.
- Não manter suporte a submissão em rascunho manual (`--noCommit`) na Microsoft Store.

## Decisions

### 1. Entrada Declarativa Única (`publicar_microsoft_store`)
- **Decisão**: Substituir o antigo parâmetro `should_publish` por `publicar_microsoft_store` com valor padrão `false`.
- **Motivação**: Atende diretamente à necessidade de simplicidade e intenção do usuário: um único botão para "Lançar na Microsoft Store".
- **Alternativas consideradas**: Manter um segundo seletor para modo rascunho (`--noCommit`). Rejeitada conforme decisão do usuário, simplificando o fluxo para ir 100% direto para revisão.

### 2. Execução Sequencial Prioritária do Canal Beta
- **Decisão**: Executar a compilação e publicação no canal Beta imediatamente após os testes unitários. Os passos da Microsoft Store são executados em seguida apenas se a flag estiver habilitada.
- **Motivação**: O canal Beta é o cenário mais frequente. Nos lançamentos regulares, a compilação de produção e as chamadas da API da Microsoft são ignoradas imediatamente, liberando o pacote Beta em tempo recorde.
- **Alternativas consideradas**: Jobs paralelos no GitHub Actions. Rejeitada porque runners Windows têm alto tempo de provisionamento e duplicam consumo de recursos, além de adicionar complexidade de sincronização para o push final do git.

### 3. Submissão Direta sem `--noCommit`
- **Decisão**: No passo de publicação do `msstore CLI`, invocar `msstore publish EditorAresta.msix -id <id>` sem o parâmetro `--noCommit`.
- **Motivação**: Comita a submissão no Partner Center imediatamente, fazendo com que o pacote entre automaticamente na fila de certificação e publicação, dispensando qualquer navegação manual pelo painel da Microsoft.

### 4. Condicional Unificada por Passo
- **Decisão**: Utilizar `if: ${{ inputs.publicar_microsoft_store }}` nos passos:
  - `Build PyInstaller (Produção)`
  - `Build MSIX Package (Produção)`
  - `Disponibilizar pacote MSIX no GitHub`
  - `Setup MS Store CLI`
  - `Publish to MS Store`

## Risks / Trade-offs

- **[Risco]** Erro na publicação da Microsoft Store após o canal Beta já ter sido enviado para o R2.
  - **Mitigação**: Os passos de avanço da versão (`-dev`) e o `git push` oficial da tag e da branch `main` encontram-se ao final do job. Se o upload para a Microsoft Store falhar, o runner aborta e nenhuma tag inconsistente é empurrada para o repositório central.
- **[Risco]** Envio inadvertido de versão com falha para certificação na loja.
  - **Mitigação**: O padrão é desmarcado (`false`). Além disso, toda execução passa obrigatoriamente pela suíte completa de testes do repositório (`uv run pytest`) antes de qualquer compilação de binários.
