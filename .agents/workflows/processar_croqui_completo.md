---
description: Orquestrador completo para conversão de croqui em formato PDF para dado estruturado
---

Este workflow atua como o Agente Orquestrador para a conversão de um croqui PDF inteiro. Você delegará tarefas pesadas para sub-agentes, controlará o fluxo do processo analisando quais arquivos já foram gerados na pasta `database/<croqui>`, e implementará rotinas de auto-correção (auto-heal) caso algum sub-agente falhe.

Para iniciar esse workflow, você receberá um arquivo PDF (Fase 1) ou uma pasta de croqui dentro de `database/` (Fase 2 ou Fase 3).

> [!IMPORTANT] 
> **Ação Orquestrada:** Você é o orquestrador. Nunca leia o PDF de capa a capa nem faça a extração massiva você mesmo. Seu trabalho é avaliar o estado, invocar as ferramentas `define_subagent` e `invoke_subagent`, lidar com as respostas de sucesso ou erro (via auto-heal), rodar scripts de compilação Python, e pedir permissão explícita (Checkpoint) para o usuário antes de avançar de fase.

### 1. Inicialização: Definição de Sub-agentes

Sempre comece o workflow declarando as "classes" de trabalhadores que você precisa usando a ferramenta `define_subagent`. Declare as seguintes 3 classes:

- **TypeName**: `SeparadorPDF`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@separar_croqui_pdf_em_partes`.

- **TypeName**: `ConversorMarkdown`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@converter_parte_croqui_para_markdown`.

- **TypeName**: `CompiladorCroqui`
  - **system_prompt**: Siga rigorosamente as instruções da skill `@preencher_croqui_yaml`.

- **TypeName**: `ExtratorMapas`
  - **system_prompt**: Utilize a combinação das skills `@mapa_extrair_pontos_de_interesse` e `@mapa_corrigir_pontos_de_interesse`.

> [!NOTE]
> Os sub-agentes trabalharão na mesma pasta do projeto, então, ao invocá-los, utilize a configuração `Workspace: 'inherit'` no `invoke_subagent` para que eles operem nos mesmos arquivos da branch atual sem clonar workspaces.

### 2. Auto-Correção (Auto-heal)

Caso algum sub-agente reporte uma falha de execução, erro de formatação ou não consiga completar o trabalho:
1. Isole a falha (outras tarefas já concluídas na mesma fase não devem ser repetidas).
2. Tente **auto-correção**: use `invoke_subagent` novamente exclusivamente para a parte que falhou (retry), e adicione no **Prompt** do novo sub-agente o log de erro ou o motivo da falha da tentativa anterior, instruindo-o a não cometer o mesmo erro.
3. Permita até **3 retentativas** por item falho. Se na 3ª tentativa ele falhar, não tente adivinhar: aguarde todos os outros sub-agentes terminarem, pause a execução e avise o usuário apontando o arquivo defeituoso e a falha para intervenção manual.

### 3. Máquina de Estados (State Check)

Sempre verifique o sistema de arquivos antes de começar para deduzir de qual fase continuar:

- Se a pasta do croqui (baseada no nome sugerido) não existir em `database/`, comece na **Fase 1**.
- Se a pasta existe e possui um arquivo `partes.json`, mas existem arquivos `.pdf` na pasta `raw_pdf_contents` sem os respectivos arquivos `.md` gerados na raiz da pasta do croqui, vá para a **Fase 2**.
- Se os arquivos `.md` de cada parte existem e o `compilado.md` já foi gerado, avance para a verificação/extração de mapas na **Fase 3**.

---

### Fase 1: Preparação do PDF

1. Invoque (usando `invoke_subagent`) um único sub-agente do tipo `SeparadorPDF` enviando o PDF completo. 
2. A tarefa do sub-agente é inspecionar o PDF visualmente, criar a pasta do croqui apropriada em `database/`, gerar o `partes.json` e **retornar para você o caminho da pasta criada**.
4. Copie o PDF original para `database/<croqui>/raw_original_pdf/croqui_original.pdf`.
5. Execute `python scripts/repartir_pdf.py database/<croqui>` para desmembrar os `.pdf` menores na pasta `raw_pdf_contents`.
6. **[Checkpoint]** Pause a execução. Pergunte ao usuário: *"As partes e imagens foram geradas corretamente? Posso prosseguir com a Fase 2 (Conversão)?"*

### Fase 2: Conversão Paralela para Markdown

1. Leia o `partes.json` da pasta para mapear quais partes compõem o croqui.
2. Usando um único chamado da tool `invoke_subagent` (enviando um array de Subagents), dispare os agentes do tipo `ConversorMarkdown` em **paralelo**, criando um agente para cada arquivo `<parte>.pdf` na pasta `raw_pdf_contents` que ainda não tenha o `.md` gerado.
3. Aguarde o retorno das mensagens de todos os sub-agentes. Caso algum sub-agente falhe, aplique imediatamente o **Auto-Correção (Auto-heal)** descrito na seção 2.
4. Após o sucesso de todas as partes, invoque um único sub-agente do tipo `CompiladorCroqui`. A missão dele será gerar o `croqui.yaml`, rodar os scripts de compilação/deploy e validar o protobuf iterativamente até que não existam erros ou warnings.
5. Aguarde o `CompiladorCroqui` retornar sucesso. Caso ele falhe por não conseguir resolver um erro de compilação antes de morrer ou devolver uma resposta de erro, aplique a lógica de **Auto-Correção** (Auto-heal) recriando o `CompiladorCroqui` com o log de erro.
6. Quando o `CompiladorCroqui` finalizar garantindo a ausência de erros, **[Checkpoint]** pause a execução. Pergunte ao usuário: *"O compilado foi gerado e validado. Por favor, rode o editor de croquis (`python editor/main.py database/<croqui>`) e confira os dados, principalmente se as imagens do croqui estão corretas na aba de imagens. Posso prosseguir com a Fase 3 (Extração de Mapas)?"*

### Fase 3: Extração de Informações dos Mapas

1. Execute `python scripts/preparar_extracao_de_mapas.py database/<croqui>`.
2. Dispare sub-agentes do tipo `ExtratorMapas` em paralelo usando a ferramenta `invoke_subagent`.
   > [!IMPORTANT]
   > **Limite de Lote (Batching):** Cada sub-agente deve processar no máximo **8 mapas**. Divida os arquivos de mapas restantes em lotes de no máximo 8 unidades por sub-agente. Isso evita que a execução exceda o limite de 1 hora de expiração de token/sessão das credenciais do sub-agente, mantendo o processo estável.
3. A missão de cada sub-agente é identificar pontos e corrigir a posição (caixas de contenção) usando as detecções do OCR e do JSON do respectivo setor.
4. Aguarde a conclusão de todos. Se houver falha na iteração das boxes, aplique a lógica de **Auto-Correção** para repassar o loop visual de `visualizar_mapa_processado.py` ao sub-agente.
5. Quando todos concluírem com sucesso, execute `python scripts/finalizar_mapas.py database/<croqui>` para transferir os dados do JSON para o Markdown correspondente.
6. Invoque novamente o sub-agente `CompiladorCroqui` para compilar o projeto inteiro garantindo que a sintaxe final, com os novos pontos no Markdown, seja perfeitamente válida. Caso ele falhe, aplique a lógica de **Auto-Correção** (Auto-heal) exatamente como na Fase 2.
7. **[Conclusão]** Volte ao usuário. Comunique que o pipeline foi concluído com absoluto sucesso. Instrua-o a rodar o editor de croquis (`python editor/main.py database/<croqui>`) e conferir os dados, principalmente se os mapas do croqui estão corretos na aba de mapas.
