---
description: Orquestrador completo para atualização de um croqui PDF existente para uma nova versão
---

Este workflow atua como o Agente Orquestrador para a atualização de um croqui que já foi processado anteriormente, aproveitando o máximo de informações e arquivos Markdown já existentes.
Você delegará tarefas pesadas para sub-agentes, controlará o fluxo do processo usando os arquivos do repositório antigo como base (arquivos com sufixo `_old`), e implementará rotinas de auto-correção (auto-heal) caso algum sub-agente falhe.

Para iniciar esse workflow, você precisará receber do usuário o caminho do novo PDF e a pasta do croqui já existente (ex: `database/br_mg_ouro_preto_ouroboulder`).

> [!IMPORTANT] 
> **Ação Orquestrada:** Você é o orquestrador. Nunca leia o PDF de capa a capa nem faça a atualização massiva você mesmo. Seu trabalho é avaliar o estado, invocar as ferramentas `define_subagent` e `invoke_subagent`, lidar com as respostas de sucesso ou erro (via auto-heal), rodar scripts de compilação Python, e pedir permissão explícita (Checkpoint) para o usuário antes de avançar de fase.

### 1. Inicialização: Definição de Sub-agentes

Sempre comece o workflow declarando as "classes" de trabalhadores que você precisa usando a ferramenta `define_subagent`. Declare as seguintes 3 classes:

- **TypeName**: `SeparadorPDF`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@separar_croqui_pdf_em_partes`.

- **TypeName**: `ConversorMarkdown`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@converter_parte_croqui_para_markdown`. Você também deve ser capaz de receber arquivos PDF e Markdown antigos para comparar e apenas atualizar o que mudou.

- **TypeName**: `CompiladorCroqui`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@preencher_croqui_yaml`.

- **TypeName**: `ExtratorMapas`
  - **system_prompt**: Utilize a combinação das skills `@mapa_extrair_pontos_de_interesse` e `@mapa_corrigir_pontos_de_interesse`. Você deve ser capaz de comparar as imagens dos mapas antigos e novos.

> [!NOTE]
> Os sub-agentes trabalharão na mesma pasta do projeto, então, ao invocá-los, utilize a configuração `Workspace: 'inherit'` no `invoke_subagent` para que eles operem nos mesmos arquivos da branch atual sem clonar workspaces.

### 2. Auto-Correção (Auto-heal)

Caso algum sub-agente reporte uma falha de execução, erro de formatação ou não consiga completar o trabalho:
1. Isole a falha (outras tarefas já concluídas na mesma fase não devem ser repetidas).
2. Tente **auto-correção**: use `invoke_subagent` novamente exclusivamente para a parte que falhou (retry), e adicione no **Prompt** do novo sub-agente o log de erro ou o motivo da falha da tentativa anterior, instruindo-o a não cometer o mesmo erro.
3. Permita até **3 retentativas** por item falho. Se na 3ª tentativa ele falhar, pause a execução e avise o usuário apontando a falha para intervenção manual.

---

### Fase 0: Preparação do Ambiente (Backup)

1. Você receberá o caminho do novo PDF e a pasta do croqui (`database/<croqui>`).
2. Utilizando os comandos do terminal, renomeie os arquivos e pastas atuais para usarem o sufixo `_old`:
   - `partes.json` -> `partes_old.json`
   - `raw_pdf_contents/` -> `raw_pdf_contents_old/`
   - `raw_original_pdf/` -> `raw_original_pdf_old/`
3. Crie a nova pasta `raw_original_pdf` e copie o novo PDF para lá com o nome de `croqui_original.pdf`.

### Fase 1: Preparação do NOVO PDF

1. Invoque (usando `invoke_subagent`) o sub-agente do tipo `SeparadorPDF` enviando o novo PDF. A tarefa dele é inspecionar o PDF visualmente e gerar o novo `partes.json` na raiz da pasta do croqui.
2. Aguarde a conclusão.
3. Execute `python scripts/repartir_pdf.py database/<croqui>` para desmembrar o novo PDF na pasta `raw_pdf_contents`.
4. **[Checkpoint]** Pause a execução. Pergunte ao usuário: *"O novo `partes.json` e as imagens foram gerados corretamente na pasta raw_pdf_contents? Posso prosseguir com a Fase 2 (Conversão e Diffing)?"*

### Fase 2: Conversão & Atualização (Diffing)

1. Leia os arquivos `partes_old.json` e `partes.json`.
2. Usando um único chamado da tool `invoke_subagent` (enviando um array de Subagents), dispare agentes do tipo `ConversorMarkdown` em **paralelo** para cada parte listada no *novo* `partes.json`:
   - **Para partes que já existiam (mesmo nome no old)**: No prompt, instrua: *"O arquivo `<parte>.md` já existe baseado em uma versão antiga do croqui. Fornecemos o PDF antigo (`raw_pdf_contents_old/<parte>.pdf`) e o novo (`raw_pdf_contents/<parte>.pdf`). Primeiro, compare visualmente o PDF antigo e o novo. Se forem essencialmente iguais em conteúdo (sem novas vias, sem mudanças de texto ou layout de mapas), não altere o arquivo `.md` e apenas responda 'Nenhuma mudança necessária'. Se houver diferenças, use as novas informações do PDF para atualizar o `.md`. Preserve as IDs de mapas na seção `referencias`, preserve formatações e links sempre que o conteúdo permanecer inalterado na nova edição."*
   - **Para partes novas**: Instrua o sub-agente a converter do zero baseando-se apenas no novo PDF em `raw_pdf_contents`.
3. Aguarde o retorno de todos. Se houver falhas, aplique a **Auto-Correção**.
4. Invoque o sub-agente `CompiladorCroqui` para compilar o projeto (gerar yaml, validar protobuf).
5. Quando finalizar com sucesso, **[Checkpoint]** pause a execução. Pergunte ao usuário: *"Os arquivos markdown foram atualizados e o projeto compilado. Por favor, confira no editor local se os textos foram mesclados corretamente. Posso prosseguir com a Fase 3 (Atualização de Mapas)?"*

### Fase 3: Re-Extração de Mapas

1. Execute `python scripts/preparar_extracao_de_mapas.py database/<croqui>`.
2. Dispare sub-agentes do tipo `ExtratorMapas` em paralelo usando a ferramenta `invoke_subagent`.
   > [!IMPORTANT]
   > **Limite de Lote (Batching):** Cada sub-agente deve processar no máximo **8 mapas**. Divida os arquivos de mapas restantes em lotes.
3. No prompt dos sub-agentes `ExtratorMapas`, instrua: *"Você tem o mapa antigo (`raw_pdf_contents_old/imagens/...`) e o novo mapa (`raw_pdf_contents/imagens/...`). Compare visualmente o mapa antigo com o novo. Se o enquadramento, zoom e a posição das vias estiverem visualmente idênticos, responda 'Nenhuma mudança necessária'. Caso tenha tido alteração no mapa (mesmo que um leve deslocamento), re-faça a extração das coordenadas para o novo JSON. Lembre-se que as IDs já constam no `.md` atualizado."*
4. Aguarde a conclusão de todos.
5. Quando todos concluírem com sucesso, execute `python scripts/finalizar_mapas.py database/<croqui>` para transferir os novos dados do JSON para o Markdown correspondente.
6. Invoque o `CompiladorCroqui` novamente para garantir que a sintaxe final seja válida.
7. **[Conclusão]** Volte ao usuário e comunique que o pipeline de atualização foi concluído com absoluto sucesso. Instrua-o a rodar o editor de croquis para conferir os mapas.
