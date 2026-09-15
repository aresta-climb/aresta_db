## Context

No modo local, o salvamento de um croqui desencadeia a serialização dos arquivos Markdown e YAML pela thread principal (`croqui_model.py`), seguida imediatamente pelo acionamento de `TarefaSalvamento` (`QThread`), que invoca o pipeline de compilação `deploy()` $\rightarrow$ `corrigir_database()` $\rightarrow$ `garantir_comentarios_licenca()`.
Como os arquivos eram serializados sem os comentários SPDX, a compilação tentava reescrever imediatamente todos os arquivos em disco. O Windows File Watcher do Git e do VS Code abria esses arquivos via `mmap` para cálculo de diff/status, bloqueando a reabertura para truncamento (`open(..., "w")`) com o erro de kernel `ERROR_USER_MAPPED_FILE` (1224), mapeado para `[Errno 22] Invalid argument`.

## Goals / Non-Goals

**Goals:**
- Eliminar o ciclo de *double-write* injetando os comentários SPDX e Copyright diretamente no primeiro salvamento de Markdown e YAML no Editor e nas bibliotecas de submissão.
- Assegurar que `garantir_comentarios_licenca` não realize operações de I/O em disco quando os arquivos já possuírem os cabeçalhos válidos.
- Implementar resiliência com política de retentativa curta e backoff em `garantir_comentarios_licenca` caso ocorram erros transitórios de bloqueio de arquivo no Windows (`OSError`).
- Manter 100% de cobertura de testes unitários e respeito aos princípios de engenharia descritos em `AGENTS.md`.

**Non-Goals:**
- Substituir o parser `PyYAML` ou criar abstrações complexas para serialização de comentários AST.
- Alterar as regras de validação semântica do compilador (como duplicidade de referências em mapas).
- Modificar o comportamento do `LocalRepoWorkspace` além da cadeia de persistência.

## Decisions

### Decisão 1: Injeção Nativa de SPDX no Frontmatter e YAML

Nas funções responsáveis por escrever arquivos Markdown com frontmatter e arquivos `croqui.yaml`, emitir o cabeçalho SPDX/Copyright diretamente na geração do texto do arquivo:
1. `editor/models/croqui_model.py` (`_salvar_objeto_com_frontmatter`):
   Ao escrever o arquivo, emitir:
   ```markdown
   ---
   # SPDX-License-Identifier: ODbL-1.0
   # Copyright (C) 2026 Aresta Climb Contributors
   <yaml_dump>
   ---
   <descricao>
   ```
2. `scripts/preparar_submissao_lib.py` (`salvar_md_com_frontmatter`):
   Garantir a mesma estrutura padronizada com as duas linhas de licença logo abaixo do `---`.
3. `editor/core/worker.py` (`TarefaSalvamento.run`):
   Ao salvar `croqui.yaml`, prefixar o conteúdo com as linhas de licença:
   ```yaml
   # SPDX-License-Identifier: ODbL-1.0
   # Copyright (C) 2026 Aresta Climb Contributors
   ```
4. *Alternativa considerada*: Tentar usar bibliotecas como `ruamel.yaml` para manter comentários.
   *Motivo do descarte*: `ruamel.yaml` adiciona dependência externa pesada, tem comportamento imprevisível em certas tipagens do Protobuf e viola o princípio de Simplicidade e Anti-Abstração (`AGENTS.md`). Injetar strings brutas no topo é simples, previsível e determinístico.

### Decisão 2: Retentativa Curta com Backoff em `garantir_comentarios_licenca`

Quando `garantir_comentarios_licenca` precisar reescrever um arquivo (caso um arquivo tenha sido criado externamente ou manualmente sem licença):
- Envolver a abertura `open(file_path, "w", encoding="utf-8")` em um loop de até 3 tentativas.
- Capturar `OSError` (abrangendo `[Errno 22] Invalid argument` e `[Errno 13] Permission denied`).
- Aguardar pequenos intervalos lineares/exponenciais (`time.sleep(0.05 * tentativa)`).
- *Alternativa considerada*: Usar `os.replace` via arquivo temporário.
   *Motivo do descarte*: Conforme comprovado experimentalmente no Windows, se o arquivo alvo possuir uma seção `mmap` ativa, o comando `os.replace` também falha com `[WinError 5] Access is denied`. A retentativa é indispensável para permitir que o Git ou indexador conclua sua leitura transitória.

## Risks / Trade-offs

- **[Risco] Duplicação acidental de comentários SPDX:** Se o dicionário original já tiver comentários ou se a rotina rodar múltiplas vezes, poderiam acumular linhas duplicadas.
  $\rightarrow$ *Mitigação*: Tanto a rotina de injeção quanto `garantir_comentarios_licenca` limpam e ignoram linhas antigas de licença antes de injetar o cabeçalho consolidado.
- **[Risco] Atraso perceptual no salvamento:** O loop de retentativa poderia causar latência na interface gráfica.
  $\rightarrow$ *Mitigação*: Como os arquivos já serão salvos com SPDX no primeiro write, a retentativa nunca será acionada em operações normais. Se for acionada em casos anômalos, os sleeps somam no máximo ~350ms e são executados na `TarefaSalvamento` (`QThread`), sem bloquear a UI.
